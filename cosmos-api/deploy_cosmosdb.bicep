//https://learn.microsoft.com/azure/cosmos-db/nosql/vector-search

param cosmosDbName string

var cosmosDbAccountName string = '${cosmosDbName}-cosmos'
var cosmosDbDatabaseName string = '${cosmosDbName}-cosmosdb'
var cosmosDbContainerName string = '${cosmosDbName}-cosmoscont'
var location string = resourceGroup().location


resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: toLower(cosmosDbAccountName)  // Cosmos DB names must be lowercase
  location: location
  properties: {
    enableFreeTier: true               // FREE TIER ENABLED - 25GB + 1000 RU/s free
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'  // Recommended consistency level for most applications, balancing performance and data freshness
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    enableAutomaticFailover: false      // Disabled for free tier optimization
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    capabilities: [
      {
        name: 'EnableNoSQLVectorSearch'  // Enables vector search on the account; index type is set per container
      }
    ]
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: {
    environment: 'development'
    purpose: 'document_vector_searching-for-ai-agent'
  }
}

// Database for storing documents and their embeddings
resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-11-15' = {
  parent: cosmosDbAccount
  name: cosmosDbDatabaseName
  properties: {
    resource: {
      id: cosmosDbDatabaseName
    }
  }
}

// Container with DiskANN vector index and global partition key
resource cosmosContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: cosmosDatabase
  name: cosmosDbContainerName
  properties: {
    resource: {
      id: cosmosDbContainerName
      partitionKey: {
        paths: [
          '/partitionKey'     // Global partition key - all documents share the same partition
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          { path: '/*' }
        ]
        excludedPaths: [
          { path: '/"_etag"/?' }
          { path: '/embedding/*' }  // Keep vectors out of the range index; the vector index below covers them
        ]
        // DISKANN Vector Index (Cosmos DB manages the DiskANN tuning parameters)
        vectorIndexes: [
          {
            path: '/embedding'
            type: 'diskANN'
          }
        ]
      }
      // Vector Embedding Policy
      // when you write the embedding call, pass the size yourself:
      // client.embeddings.create(model=deployment_name, input=text, dimensions=512)
      vectorEmbeddingPolicy: {
        vectorEmbeddings: [
          {
            path: '/embedding'
            dataType: 'float32'
            dimensions: 512           // text-embedding-3-small called with dimensions=512
            distanceFunction: 'cosine'
          }
        ]
      }
      defaultTtl: 7776000  // 90 days TTL
    }
    options: {
      throughput: 1000 // This will be FREE under the free tier (first 1000 RU/s)
    }
  }
}

output COSMOS_DB_ENDPOINT string = cosmosDbAccount.properties.documentEndpoint
// az cosmosdb keys list --name jimcosmosai200-cosmos --resource-group rg-cosmos-api --query primaryMasterKey -o tsv
// output COSMOS_PRIMARY_KEY string = cosmosDbAccount.listKeys().primaryMasterKey
output COSMOS_DB_NAME string = cosmosDatabase.name
output COSMOS_CONTAINER_NAME string = cosmosContainer.name
