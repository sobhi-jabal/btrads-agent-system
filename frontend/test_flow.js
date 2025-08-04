// Test the complete CSV upload flow
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

async function testFlow() {
  console.log('1. Testing backend is responsive...');
  try {
    const health = await axios.get('http://localhost:8001/api/patients/');
    console.log('   ✓ Backend is running, found', health.data.length, 'patients');
  } catch (e) {
    console.error('   ✗ Backend error:', e.message);
    return;
  }
  
  console.log('\n2. Creating test CSV...');
  const csv = `patient_id,clinical_note
FLOW001,"Test patient 1 with glioma"
FLOW002,"Test patient 2 post-radiation"`;
  fs.writeFileSync('test_flow.csv', csv);
  console.log('   ✓ Created test_flow.csv');
  
  console.log('\n3. Uploading CSV to backend...');
  const form = new FormData();
  form.append('file', fs.createReadStream('test_flow.csv'));
  
  try {
    const response = await axios.post('http://localhost:8001/api/patients/upload', form, {
      headers: form.getHeaders()
    });
    console.log('   ✓ Upload successful!');
    console.log('   Uploaded patients:', response.data.map(p => p.id).join(', '));
  } catch (e) {
    console.error('   ✗ Upload failed:', e.response?.data || e.message);
  }
  
  console.log('\n4. Testing frontend is responsive...');
  try {
    const frontend = await axios.get('http://localhost:3000');
    const hasCSVInput = frontend.data.includes('csv-file');
    console.log('   ✓ Frontend is running');
    console.log('   CSV input in DOM:', hasCSVInput ? 'Yes' : 'No');
  } catch (e) {
    console.error('   ✗ Frontend error:', e.message);
  }
}

testFlow();