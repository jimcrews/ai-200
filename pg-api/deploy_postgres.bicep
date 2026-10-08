param pgServername string
param pgDbname string

@description('Your public IP, to allow connections from your machine')
param clientIp string = ''

var location string = resourceGroup().location

@secure()
param passW string


resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: pgServername
  location: location
  sku: {
    name: 'Standard_B1ms' // 1 vCPU, 2 GB RAM - cheapest tier, fine for a demo
    tier: 'Burstable'
  }
  properties: {
    version: '17'
    administratorLogin: 'pgadmin'
    administratorLoginPassword: passW
    storage: {
      storageSizeGB: 32 // Smallest size available
      autoGrow: 'Disabled'
    }
    backup: {
      backupRetentionDays: 7 // Minimum allowed
      geoRedundantBackup: 'Disabled'
    }
    authConfig: {
      activeDirectoryAuth: 'Disabled'
      passwordAuth: 'Enabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
      // For production, consider restricting to specific IPs or use Private Endpoint
    }
    highAvailability: {
      mode: 'Disabled' // Disabled for cost optimization
    }
    maintenanceWindow: {
      customWindow: 'Disabled'
    }
  }
  tags: {
    environment: 'development'
    purpose: 'document_vector_searching-for-ai-agent'
  }
}

// Enable pgvector extension on the server
resource postgresExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: postgresServer
  name: 'azure.extensions'
  properties: {
    value: 'VECTOR' // Enables pgvector extension
    source: 'user-override' // Required for user-defined extensions
  }
}

// Create database for storing documents with embeddings
resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgresServer
  name: pgDbname
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
  dependsOn: [postgresExtensions]
}

// Public access is enabled but nothing can connect without firewall rules
// 0.0.0.0 is the special rule that allows Azure services (e.g. Container Apps)
resource allowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgresServer
  name: 'AllowAllAzureServicesAndResourcesWithinAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
  dependsOn: [postgresDatabase]
}

resource allowClientIp 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = if (!empty(clientIp)) {
  parent: postgresServer
  name: 'AllowClientIp'
  properties: {
    startIpAddress: clientIp
    endIpAddress: clientIp
  }
  dependsOn: [allowAzureServices]
}

output POSTGRES_HOST string = postgresServer.properties.fullyQualifiedDomainName
output POSTGRES_DB_NAME string = postgresDatabase.name
output POSTGRES_ADMIN_USERNAME string = postgresServer.properties.administratorLogin
