//https://learn.microsoft.com/azure/templates/microsoft.servicebus/namespaces

param serviceBusName string               // globally unique, 6-50 chars, becomes <name>.servicebus.windows.net
param principalId string = ''             // your user object id: az ad signed-in-user show --query id -o tsv
param location string = resourceGroup().location

var queueName string = 'summarize-jobs'
var topicName string = 'documents'
var subscriptionNames array = [
  'summarize'   // worker that summarizes each document (same job as the queue worker)
  'word-count'  // a second, independent consumer of the same documents
]

// Built-in role: send, receive and manage entities. Using DefaultAzureCredential requires a data-plane role;
// being Owner/Contributor on the resource group only covers the management plane.
var serviceBusDataOwnerRoleId string = '090c5cfd-751d-490a-894a-3ce6f1109419'

/*
  A namespace is the container for queues and topics.
  Standard tier is needed for topics/subscriptions (Basic only supports queues).
*/
resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: serviceBusName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true  // No SAS keys / connection strings; Entra ID (DefaultAzureCredential) only
  }
  tags: {
    environment: 'development'
    purpose: 'service-bus-queue-and-topic-demo'
  }
}

/*
  Queue for document summary jobs. producer.py sends to it, worker.py receives from it.
*/
resource summarizeJobsQueue 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = {
  parent: serviceBusNamespace
  name: queueName
  properties: {
    lockDuration: 'PT1M'                       // Worker has 1 minute to complete a message before it's unlocked and redelivered
    maxDeliveryCount: 5                        // After 5 failed attempts the message moves to the dead-letter queue
    defaultMessageTimeToLive: 'P1D'            // Unprocessed jobs expire after 1 day
    deadLetteringOnMessageExpiration: true     // Expired messages go to the dead-letter queue instead of being dropped
    requiresDuplicateDetection: false
    requiresSession: false
    maxSizeInMegabytes: 1024
  }
}

/*
  Topic for publish/subscribe. A producer sends each document once to the topic, and every
  subscription gets its own copy. Unlike a queue, you never receive from the topic itself.
*/
resource documentsTopic 'Microsoft.ServiceBus/namespaces/topics@2024-01-01' = {
  parent: serviceBusNamespace
  name: topicName
  properties: {
    defaultMessageTimeToLive: 'P1D'            // Messages expire after 1 day
    requiresDuplicateDetection: false
    maxSizeInMegabytes: 1024
  }
}

/*
  Subscriptions behave like queues attached to the topic: each has its own messages, locks,
  delivery counts and dead-letter queue (documents/subscriptions/<name>/$deadletterqueue).
  With no rules defined, Service Bus adds a '$Default' rule that accepts every message.
*/
resource documentsSubscriptions 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2024-01-01' = [for name in subscriptionNames: {
  parent: documentsTopic
  name: name
  properties: {
    lockDuration: 'PT1M'                       // Same settings as the queue, so the workers behave the same way
    maxDeliveryCount: 5
    defaultMessageTimeToLive: 'P1D'
    deadLetteringOnMessageExpiration: true
    requiresSession: false
  }
}]

/*
  Grant the signed-in user data-plane access so producer.py / worker.py can connect with DefaultAzureCredential.
  Skipped when principalId is not supplied.
*/
resource serviceBusDataOwnerAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(serviceBusNamespace.id, principalId, serviceBusDataOwnerRoleId)
  scope: serviceBusNamespace
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', serviceBusDataOwnerRoleId)
    principalId: principalId
    principalType: 'User'
  }
}

/*
  OUTPUTS
*/
// The SDK wants the fully qualified namespace, e.g. ServiceBusClient(fully_qualified_namespace, DefaultAzureCredential())
output SERVICEBUS_FULLY_QUALIFIED_NAMESPACE string = '${serviceBusNamespace.name}.servicebus.windows.net'
output SERVICEBUS_QUEUE_NAME string = summarizeJobsQueue.name
output SERVICEBUS_TOPIC_NAME string = documentsTopic.name
output SERVICEBUS_SUBSCRIPTION_NAMES array = [for (name, i) in subscriptionNames: documentsSubscriptions[i].name]
