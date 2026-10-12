//https://learn.microsoft.com/azure/templates/microsoft.cache/redisenterprise

param redisName string
param location string = resourceGroup().location

/*
  Azure Managed Redis for vector search (RediSearch) in the RAG pipeline
*/
resource redisEnterprise 'Microsoft.Cache/redisEnterprise@2025-07-01' = {
  name: redisName
  location: location
  properties: {
    minimumTlsVersion: '1.2'
    highAvailability: 'Disabled'
    publicNetworkAccess: 'Enabled'
  }
  sku: {
    name: 'Balanced_B0'
  }
  tags: {
    environment: 'development'
    purpose: 'vector-search-for-ai-agent'
  }
}

// Database is required for Azure Managed Redis to function
resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2025-07-01' = {
  name: 'default' // Enterprise uses database name 'default', it cannot be any other name
  parent: redisEnterprise
  properties: {
    accessKeysAuthentication: 'Enabled' // disabled by default in newer API versions
    clientProtocol: 'Encrypted'
    port: 10000
    evictionPolicy: 'NoEviction'  // required by RediSearch; also preserves vector data
    clusteringPolicy: 'EnterpriseCluster'
    modules: [
      {
        name: 'RediSearch'
      }
    ]
  }
}

output REDIS_HOSTNAME string = redisEnterprise.properties.hostName
output REDIS_PORT int = redisDatabase.properties.port
