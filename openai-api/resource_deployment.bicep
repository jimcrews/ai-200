//https://github.com/microsoft-foundry/foundry-samples/blob/main/infrastructure/infrastructure-setup-bicep/00-basic/main.bicep

param appPrefix string
param aiFoundryName string = appPrefix
param aiProjectName string = '${aiFoundryName}-proj'
param llmModelDeploymentName string = '${appPrefix}-llm-deploy'
param location string = resourceGroup().location

/*
  An AI Foundry resources is a variant of a CognitiveServices/account resource type that is specifically designed
   to host AI workloads and provide a seamless experience for deploying and managing AI models and assets.
*/ 
resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: aiFoundryName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    // required to work in AI Foundry
    allowProjectManagement: true

    // Defines developer API endpoint subdomain
    customSubDomainName: aiFoundryName

    disableLocalAuth: false
  }
}

/*
  An AI Project is a logical container for assets such as models, deployments, etc. within the AI Foundry. 
  It is required to create an AI Project before deploying any models or other assets.
*/
resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  name: aiProjectName
  parent: aiFoundry
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

/*
  Deploying a model to the AI Foundry is done through a deployment resource.
  In this example, we are deploying the 'gpt-4.1-mini' model, 
  which is a variant of GPT-4 optimized for lower latency and 
  cost while still providing strong performance for many use cases.
*/
// https://ai.azure.com/catalog/models/gpt-4.1-mini
resource llmModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01'= {
  parent: aiFoundry
  name: llmModelDeploymentName
  // Wait for the project; parallel child writes on the same account cause RequestConflict
  dependsOn: [
    aiProject
  ]
  sku : {
    capacity: 1
    name: 'GlobalStandard'
  }
  properties: {
    model:{
      name: 'gpt-4.1-mini'
      format: 'OpenAI'
      version: '2025-04-14'
    }
  }
}

/*
  OUTPUTS
*/
output OPENAI_ENDPOINT string = 'https://${aiFoundry.properties.customSubDomainName}.services.ai.azure.com/openai/v1'
output OPENAI_API_KEY string = listKeys(aiFoundry.id, '2025-06-01').key1
output LLM_MODEL_DEPLOYMENT_NAME string = llmModelDeployment.name
