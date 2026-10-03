param acrName string
param location string = resourceGroup().location

/*
  Container Registry deployment to push containers to
*/
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic' // Cost-effective option
  }
  properties: {
    // Admin user is needed to push images from local dev environment.
    adminUserEnabled: true
  }
}

output ACR_LOGIN_SERVER string = acr.properties.loginServer
