//https://github.com/microsoft-foundry/foundry-samples/blob/main/infrastructure/infrastructure-setup-bicep/00-basic/main.bicep

param aiFoundryName string

var aiProjectName string = '${aiFoundryName}-proj'
var llmModelDeploymentName string = '${aiFoundryName}-llm-deploy'
var embeddingModelDeploymentName string = '${aiFoundryName}-emb-deploy'
var location string = resourceGroup().location


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
  Deploy Embedding model for vector generation
*/
resource embeddingModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01'= {
  parent: aiFoundry
  name: embeddingModelDeploymentName
  dependsOn: [
    llmModelDeployment  // Explicitly wait for LLM to finish first
  ]
  sku : {
    capacity: 10  // units of 1K tokens/min; capacity 1 caused 429s (60s retry waits) during upload
    name: 'GlobalStandard'
  }
  properties: {
    model:{
      name: 'text-embedding-3-small'  // 1536 dims by default; can be reduced via the `dimensions` request param
      format: 'OpenAI'
      version: '1'
    }
  }
}

/*
  OUTPUTS
*/
output OPENAI_ENDPOINT string = 'https://${aiFoundry.properties.customSubDomainName}.services.ai.azure.com/openai/v1'
// az cognitiveservices account keys list --name jimfoundryai200 --resource-group rg-cosmos-api --query key1 -o tsv
// output OPENAI_API_KEY string = aiFoundry.listKeys().key1
output LLM_MODEL_DEPLOYMENT_NAME string = llmModelDeployment.name
output EMBEDDING_MODEL_DEPLOYMENT_NAME string = embeddingModelDeployment.name
