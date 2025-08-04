// Test script to simulate CSV upload
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Create a test CSV file
const testCSV = `patient_id,clinical_note
PT001,"Test patient with glioblastoma. Post-surgical resection."
PT002,"Brain tumor patient receiving radiation therapy."`;

fs.writeFileSync('test_sample.csv', testCSV);

async function testCSVUpload() {
  const browser = await puppeteer.launch({ 
    headless: false, 
    devtools: true 
  });
  const page = await browser.newPage();
  
  // Enable console logging
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  
  try {
    console.log('1. Navigating to localhost:3000...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle2' });
    
    console.log('2. Looking for Batch Processing section...');
    // Click on Batch Processing to expand it
    const batchProcessing = await page.waitForSelector('text/Batch Processing', { timeout: 5000 });
    await batchProcessing.click();
    console.log('   - Clicked Batch Processing');
    
    await page.waitForTimeout(1000);
    
    console.log('3. Looking for file input...');
    // Check if file input exists
    const fileInputExists = await page.evaluate(() => {
      const input = document.getElementById('csv-file');
      console.log('File input found:', input);
      return input !== null;
    });
    console.log('   - File input exists:', fileInputExists);
    
    console.log('4. Trying to upload file...');
    // Try to upload file
    const fileInput = await page.$('#csv-file');
    if (fileInput) {
      await fileInput.uploadFile(path.resolve('test_sample.csv'));
      console.log('   - File uploaded');
    } else {
      console.log('   - ERROR: Could not find file input');
    }
    
    await page.waitForTimeout(2000);
    
    console.log('5. Checking if validator appeared...');
    const validatorVisible = await page.evaluate(() => {
      const elements = Array.from(document.querySelectorAll('*'));
      return elements.some(el => el.textContent?.includes('CSV Validation'));
    });
    console.log('   - Validator visible:', validatorVisible);
    
  } catch (error) {
    console.error('Error during test:', error);
  }
  
  // Keep browser open for inspection
  console.log('\nTest complete. Browser will stay open for inspection.');
  console.log('Press Ctrl+C to exit.');
}

testCSVUpload();