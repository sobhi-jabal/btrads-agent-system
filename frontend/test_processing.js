// Test the processing flow
const axios = require('axios');

async function testProcessing() {
  console.log('Testing Processing Flow');
  console.log('=' .repeat(50));
  
  try {
    // 1. Create a test patient with simple clinical note
    console.log('\n1. Creating test patient...');
    const patientData = {
      clinical_note: `
        Patient with glioblastoma. 
        Currently on dexamethasone 4mg daily for edema control.
        Radiation therapy completed on 05/15/2023.
        MRI shows stable disease compared to prior.
      `,
      baseline_date: '2023-03-01',
      followup_date: '2023-12-01'
    };
    
    const createResp = await axios.post('http://localhost:8001/api/patients/', patientData);
    const patientId = createResp.data.id;
    console.log('   ✓ Patient created:', patientId);
    
    // 2. Start processing
    console.log('\n2. Starting processing...');
    const processResp = await axios.post(`http://localhost:8001/api/patients/${patientId}/process`);
    console.log('   ✓ Processing completed');
    
    // 3. Check the result
    if (processResp.data) {
      console.log('\n3. Processing Result:');
      console.log('   Score:', processResp.data.score || 'Not determined');
      console.log('   Reasoning:', processResp.data.reasoning || 'N/A');
      console.log('   Patient ID:', processResp.data.patient_id);
      
      if (processResp.data.algorithm_path) {
        console.log('   Path nodes:', processResp.data.algorithm_path.nodes?.length || 0);
      }
    }
    
    // 4. Check patient status
    console.log('\n4. Checking patient status...');
    const statusResp = await axios.get(`http://localhost:8001/api/patients/${patientId}`);
    console.log('   Processing status:', statusResp.data.processing_status);
    console.log('   Current node:', statusResp.data.current_node || 'N/A');
    
    console.log('\n✅ Processing flow is working!');
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.response?.data || error.message);
    if (error.response?.status === 500) {
      console.error('   Server error - check backend logs');
    }
  }
}

testProcessing();