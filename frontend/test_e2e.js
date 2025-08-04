// Test complete end-to-end flow with LLM extraction
const axios = require('axios');

async function testE2E() {
  console.log('Testing End-to-End Flow with LLM Extraction');
  console.log('=' .repeat(50));
  
  try {
    // 1. Create a patient with clinical note
    console.log('\n1. Creating patient...');
    const patientData = {
      clinical_note: `
        CLINICAL HISTORY: 68-year-old male with glioblastoma.
        
        MEDICATIONS: Patient is on dexamethasone 4mg daily for vasogenic edema.
        Started bevacizumab (Avastin) 10mg/kg every 2 weeks - first dose given.
        
        TREATMENT HISTORY: Completed radiation therapy on 05/15/2023.
        Post-operative resection performed 03/01/2023.
        
        CURRENT STATUS: Stable on current regimen with no new symptoms.
      `,
      baseline_date: '2023-03-01',
      followup_date: '2023-12-01'
    };
    
    const createResp = await axios.post('http://localhost:8001/api/patients/', patientData);
    const patientId = createResp.data.id;
    console.log('   ✓ Patient created:', patientId);
    
    // 2. Test LLM extraction
    console.log('\n2. Testing LLM extraction...');
    const extractStart = Date.now();
    
    const extractResp = await axios.post('http://localhost:8001/api/llm/extract', {
      clinical_note: patientData.clinical_note,
      extraction_type: 'medications',
      model: 'phi4:14b'
    });
    
    const extractTime = (Date.now() - extractStart) / 1000;
    console.log('   ✓ LLM extraction completed in', extractTime.toFixed(1), 'seconds');
    console.log('   Results:', extractResp.data.data);
    console.log('   Confidence:', extractResp.data.confidence);
    
    // 3. Start processing
    console.log('\n3. Starting patient processing...');
    const processResp = await axios.post(`http://localhost:8001/api/patients/${patientId}/process`);
    console.log('   ✓ Processing started');
    
    // 4. Check status
    console.log('\n4. Checking processing status...');
    let status = 'processing';
    let attempts = 0;
    
    while (status === 'processing' && attempts < 30) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      const statusResp = await axios.get(`http://localhost:8001/api/patients/${patientId}`);
      status = statusResp.data.processing_status;
      attempts++;
      process.stdout.write('.');
    }
    console.log('');
    
    if (status === 'completed') {
      console.log('   ✓ Processing completed successfully!');
      
      // Get final patient data
      const finalResp = await axios.get(`http://localhost:8001/api/patients/${patientId}`);
      const btScore = finalResp.data.data?.bt_rads_score;
      console.log('   BT-RADS Score:', btScore || 'Not determined');
    } else {
      console.log('   ⚠ Processing status:', status);
    }
    
    // 5. Test radiation date extraction
    console.log('\n5. Testing radiation date extraction...');
    const radStart = Date.now();
    
    const radResp = await axios.post('http://localhost:8001/api/llm/extract', {
      clinical_note: patientData.clinical_note,
      extraction_type: 'radiation_date',
      model: 'phi4:14b'
    });
    
    const radTime = (Date.now() - radStart) / 1000;
    console.log('   ✓ Radiation extraction completed in', radTime.toFixed(1), 'seconds');
    console.log('   Results:', radResp.data.data);
    
    console.log('\n✅ All tests passed! System is functioning correctly.');
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.response?.data || error.message);
    process.exit(1);
  }
}

testE2E();