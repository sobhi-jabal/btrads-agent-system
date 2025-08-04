"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { 
  FileText, 
  Upload, 
  AlertCircle, 
  ChevronRight,
  Loader2,
  User,
  Calendar,
  Activity,
  ChevronDown,
  ChevronUp,
  Database,
  FileSpreadsheet,
  Check,
  Brain,
  Zap,
  Settings
} from "lucide-react";
import { BTRADSDecisionFlow } from "@/components/flow/BTRADSDecisionFlow";
import { CSVValidator } from "@/components/csv/CSVValidator";
import { PatientData } from "@/types/patient";
import { api } from "@/lib/api/client";

export default function Home() {
  const [activePatientId, setActivePatientId] = useState<string | null>(null);
  const [clinicalNote, setClinicalNote] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedPatients, setUploadedPatients] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [csvData, setCsvData] = useState<any[]>([]);
  const [showValidator, setShowValidator] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Expandable sections state
  const [expandedSection, setExpandedSection] = useState<string | null>("new-analysis");
  
  // Processing tracking state
  const [processedPatientIds, setProcessedPatientIds] = useState<Set<string>>(new Set());
  const [allPatients, setAllPatients] = useState<any[]>([]);
  
  // Extraction settings
  const [extractionMode, setExtractionMode] = useState<'nlp' | 'llm' | 'both'>('llm');

  // Initialize - Don't load old patients on startup
  useEffect(() => {
    // Comment out to prevent loading old patients
    // fetchAllPatients();
    
    // Start with clean state
    setAllPatients([]);
    setUploadedPatients([]);
  }, []);
  
  // Fetch all patients - DISABLED to prevent loading old patients
  const fetchAllPatients = async () => {
    // DISABLED - We don't want to load patients from database
    // try {
    //   const patients = await api.patients.list();
    //   setAllPatients(patients);
    //   setUploadedPatients(patients);
    // } catch (error) {
    //   console.error("Error fetching patients:", error);
    // }
    console.log("fetchAllPatients called but disabled to prevent loading old patients");
  };

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const handleSubmit = async () => {
    if (!clinicalNote.trim()) return;

    setIsProcessing(true);
    setError(null);
    setSuccess(null);
    
    try {
      const patientData: Partial<PatientData> = {
        clinical_note: clinicalNote,
        baseline_date: new Date().toISOString().split('T')[0],
        followup_date: new Date().toISOString().split('T')[0],
      };

      const patient = await api.patients.create(patientData);
      setActivePatientId(patient.id);
      
      await api.patients.startProcessing(patient.id, false);
      setSuccess("Analysis started successfully");
      setExpandedSection("results");
    } catch (error) {
      console.error("Error processing patient:", error);
      setError("Failed to start analysis. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    console.log('[Upload] File selected:', file.name);
    setError(null);
    setSuccess(null);
    
    // Auto-expand CSV upload section when file is selected
    setExpandedSection("csv-upload");
    
    try {
      const text = await file.text();
      
      // Parse CSV properly handling quoted fields and multiline values
      const parseCSV = (text: string): any[] => {
        const records: any[] = [];
        const headers: string[] = [];
        let currentRecord: string[] = [];
        let currentField = '';
        let inQuotes = false;
        let isHeader = true;
        
        for (let i = 0; i < text.length; i++) {
          const char = text[i];
          const nextChar = text[i + 1];
          
          if (char === '"') {
            if (inQuotes && nextChar === '"') {
              // Escaped quote
              currentField += '"';
              i++; // Skip next quote
            } else {
              // Toggle quote state
              inQuotes = !inQuotes;
            }
          } else if (char === ',' && !inQuotes) {
            // End of field
            currentRecord.push(currentField.trim());
            currentField = '';
          } else if ((char === '\n' || char === '\r') && !inQuotes) {
            // End of record (but not if we're inside quotes)
            if (char === '\r' && nextChar === '\n') {
              i++; // Skip \n in \r\n
            }
            
            // Add the last field
            currentRecord.push(currentField.trim());
            currentField = '';
            
            // Process the record
            if (currentRecord.length > 0 && currentRecord.some(f => f !== '')) {
              if (isHeader) {
                headers.push(...currentRecord);
                isHeader = false;
              } else {
                // Create object from headers and values
                const obj: any = {};
                headers.forEach((header, index) => {
                  obj[header] = currentRecord[index] || '';
                });
                records.push(obj);
              }
            }
            
            currentRecord = [];
          } else {
            // Regular character
            currentField += char;
          }
        }
        
        // Don't forget the last field and record if file doesn't end with newline
        if (currentField || currentRecord.length > 0) {
          currentRecord.push(currentField.trim());
          if (currentRecord.length > 0 && currentRecord.some(f => f !== '')) {
            if (isHeader) {
              headers.push(...currentRecord);
            } else {
              const obj: any = {};
              headers.forEach((header, index) => {
                obj[header] = currentRecord[index] || '';
              });
              records.push(obj);
            }
          }
        }
        
        // Filter out completely empty rows
        return records.filter(row => 
          Object.values(row).some(v => v !== null && v !== undefined && String(v).trim() !== '')
        );
      };
      
      const data = parseCSV(text);
      console.log('[Upload] CSV parsed, rows:', data.length);

      setCsvData(data);
      setShowValidator(true);
    } catch (error) {
      console.error("[Upload] Error reading file:", error);
      setError("Failed to read CSV file. Please check the format.");
    }
  };

  const handleValidationComplete = async (result: any) => {
    console.log('[Upload] handleValidationComplete called with:', result);
    if (result.isValid) {
      console.log('[Upload] Validation is valid, starting upload...');
      setIsProcessing(true);
      setError(null);
      try {
        // Check if we have data to process
        if (!csvData || csvData.length === 0) {
          setError('No CSV data available to upload. Please select a file again.');
          return;
        }
        
        // Create normalized data with standardized column names
        const normalizedData = csvData.map((row) => {
          const normalizedRow: any = {};
          
          // Map columns based on validation result mappings
          result.mappings.forEach((mapping: any) => {
            if (mapping.status === 'valid' && mapping.csvColumn) {
              normalizedRow[mapping.btradsField] = row[mapping.csvColumn] || '';
            }
          });
          
          return normalizedRow;
        });
        
        // Check if normalization produced data
        if (normalizedData.length === 0) {
          setError('Failed to process CSV data. Please check the file format.');
          return;
        }
        
        // Get headers from valid mappings
        const headers = result.mappings
          .filter((m: any) => m.status === 'valid')
          .map((m: any) => m.btradsField);
        
        if (headers.length === 0) {
          setError('No valid column mappings found. Please check the CSV format.');
          return;
        }
        
        // Create CSV with normalized column names
        const csvRows = normalizedData.map((row: any) => 
          headers.map((header: string) => {
            const value = row[header] || '';
            // Escape quotes and wrap in quotes if contains comma or newline
            const escaped = value.toString().replace(/"/g, '""');
            return /[,\n\r"]/.test(escaped) ? `"${escaped}"` : escaped;
          }).join(',')
        );
        
        const csvContent = [
          headers.join(','),
          ...csvRows
        ].join('\n');

        // Create a Blob and File from the CSV content
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const file = new File([blob], 'validated_data.csv', { type: 'text/csv' });

        console.log('[Upload] Uploading file to backend...');
        const patients = await api.patients.upload(file);
        console.log('[Upload] Upload successful, received patients:', patients);
        
        // Update state
        setUploadedPatients(patients);
        setAllPatients(prev => [...prev, ...patients]);
        setSuccess(`Successfully uploaded ${patients.length} patients from CSV file.`);
        setShowValidator(false);
        setCsvData([]);
        
        // Keep CSV section expanded to show the uploaded patients
        setExpandedSection("csv-upload");
        
        // Clear file input
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        
        // Refresh the patient list
        await fetchAllPatients();
        
        console.log('[Upload] Upload complete, UI updated');
      } catch (error: any) {
        console.error("[Upload] Error uploading file:", error);
        
        // Extract error message from backend response
        const errorDetail = error.response?.data?.detail;
        let errorMessage = "Failed to upload CSV file. Please check the format and try again.";
        
        if (errorDetail) {
          if (Array.isArray(errorDetail)) {
            errorMessage = errorDetail.map(err => err.msg || err.message || JSON.stringify(err)).join(", ");
          } else if (typeof errorDetail === 'string') {
            errorMessage = errorDetail;
          }
        }
        
        setError(errorMessage);
      } finally {
        setIsProcessing(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    }
  };

  const processPatient = async (patient: any) => {
    setActivePatientId(patient.id);
    setError(null);
    setSuccess(null);
    // Just set the patient and expand results - BTRADSDecisionFlow will handle the actual processing
    setExpandedSection("results");
  };
  
  // Mark patient as processed
  const markPatientAsProcessed = (patientId: string) => {
    setProcessedPatientIds(prev => new Set(prev).add(patientId));
  };
  
  // Find next unprocessed patient
  const findNextUnprocessedPatient = (currentId: string): string | null => {
    const currentIndex = allPatients.findIndex(p => p.id === currentId);
    if (currentIndex === -1) return null;
    
    // Search forward from current position
    for (let i = currentIndex + 1; i < allPatients.length; i++) {
      if (!processedPatientIds.has(allPatients[i].id)) {
        return allPatients[i].id;
      }
    }
    
    // Wrap around to beginning
    for (let i = 0; i < currentIndex; i++) {
      if (!processedPatientIds.has(allPatients[i].id)) {
        return allPatients[i].id;
      }
    }
    
    return null;
  };
  
  // Find previous unprocessed patient
  const findPreviousUnprocessedPatient = (currentId: string): string | null => {
    const currentIndex = allPatients.findIndex(p => p.id === currentId);
    if (currentIndex === -1) return null;
    
    // Search backward from current position
    for (let i = currentIndex - 1; i >= 0; i--) {
      if (!processedPatientIds.has(allPatients[i].id)) {
        return allPatients[i].id;
      }
    }
    
    // Wrap around to end
    for (let i = allPatients.length - 1; i > currentIndex; i--) {
      if (!processedPatientIds.has(allPatients[i].id)) {
        return allPatients[i].id;
      }
    }
    
    return null;
  };
  
  // Process next patient
  const processNextPatient = () => {
    if (!activePatientId) return;
    
    const nextId = findNextUnprocessedPatient(activePatientId);
    if (nextId) {
      const nextPatient = allPatients.find(p => p.id === nextId);
      if (nextPatient) {
        processPatient(nextPatient);
      }
    } else {
      setSuccess("All patients have been processed!");
    }
  };
  
  // Process previous patient
  const processPreviousPatient = () => {
    if (!activePatientId) return;
    
    const prevId = findPreviousUnprocessedPatient(activePatientId);
    if (prevId) {
      const prevPatient = allPatients.find(p => p.id === prevId);
      if (prevPatient) {
        processPatient(prevPatient);
      }
    } else {
      setSuccess("No previous unprocessed patients found.");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">BT-RADS Multi-Agent System</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Brain Tumor Reporting and Data System
              </p>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto p-6 max-w-7xl">
        {/* Alerts */}
        {error && (
          <Alert variant="destructive" className="mb-6 border-destructive/20">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        
        {success && (
          <Alert className="mb-6 border-success/20 bg-success/5">
            <Check className="h-4 w-4 text-success" />
            <AlertDescription className="text-success-foreground">
              {success}
            </AlertDescription>
          </Alert>
        )}

        {/* Flowchart-inspired sections */}
        <div className="space-y-6">
          {/* New Analysis Section */}
          <Card className={`shadow-soft transition-all duration-300 ${
            expandedSection === "new-analysis" ? "shadow-soft-lg" : ""
          }`}>
            <CardHeader 
              className="cursor-pointer"
              onClick={() => toggleSection("new-analysis")}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary rounded-md">
                    <FileText className="h-5 w-5 text-primary-foreground" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Clinical Note Analysis</CardTitle>
                    <CardDescription>
                      Analyze individual patient reports
                    </CardDescription>
                  </div>
                </div>
                {expandedSection === "new-analysis" ? (
                  <ChevronUp className="h-5 w-5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
            </CardHeader>
            
            {expandedSection === "new-analysis" && (
              <>
                <Separator />
                <CardContent className="space-y-6 pt-6">
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="clinical-note" className="text-base font-medium mb-2 block">
                        Clinical Note / Radiology Report
                      </Label>
                      <Textarea
                        id="clinical-note"
                        placeholder="Enter the clinical note or radiology report for BT-RADS classification..."
                        className="min-h-[300px] resize-none font-mono text-sm border-input"
                        value={clinicalNote}
                        onChange={(e) => setClinicalNote(e.target.value)}
                      />
                    </div>
                    
                    <Button 
                      onClick={handleSubmit}
                      disabled={isProcessing || !clinicalNote.trim()}
                      className="w-full"
                      size="lg"
                    >
                      {isProcessing ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <Activity className="mr-2 h-4 w-4" />
                          Start BT-RADS Analysis
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </>
            )}
          </Card>

          {/* Connecting line */}
          {expandedSection !== "results" && expandedSection !== "extraction-settings" && (
            <div className="flex justify-center">
              <div className="w-0.5 h-12 bg-border"></div>
            </div>
          )}

          {/* Extraction Settings Section */}
          <Card className={`shadow-soft transition-all duration-300 ${
            expandedSection === "extraction-settings" ? "shadow-soft-lg" : ""
          }`}>
            <CardHeader 
              className="cursor-pointer"
              onClick={() => toggleSection("extraction-settings")}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-100 dark:bg-purple-900/20 rounded-md">
                    <Settings className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Extraction Settings</CardTitle>
                    <CardDescription>
                      Configure how medication and radiation data is extracted
                    </CardDescription>
                  </div>
                </div>
                {expandedSection === "extraction-settings" ? (
                  <ChevronUp className="h-5 w-5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
            </CardHeader>
            
            {expandedSection === "extraction-settings" && (
              <>
                <Separator />
                <CardContent className="space-y-6 pt-6">
                  <div>
                    <Label className="text-base font-medium mb-3 block">
                      Select Extraction Method
                    </Label>
                    <RadioGroup value={extractionMode} onValueChange={(value) => setExtractionMode(value as 'nlp' | 'llm' | 'both')}>
                      <div className="space-y-4">
                        <Label className="flex items-start space-x-3 cursor-pointer p-3 rounded-lg border hover:bg-muted/50">
                          <RadioGroupItem value="nlp" className="mt-1" />
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <Zap className="h-4 w-4 text-yellow-600" />
                              <span className="font-medium">NLP Pattern Matching</span>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              Fast, regex-based extraction using predefined patterns. Best for standard report formats.
                            </p>
                          </div>
                        </Label>
                        
                        <Label className="flex items-start space-x-3 cursor-pointer p-3 rounded-lg border hover:bg-muted/50">
                          <RadioGroupItem value="llm" className="mt-1" />
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <Brain className="h-4 w-4 text-blue-600" />
                              <span className="font-medium">LLM Analysis (Ollama phi4:14b)</span>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              AI-powered, context-aware extraction for complex cases. Requires Ollama running locally.
                            </p>
                          </div>
                        </Label>
                        
                        <Label className="flex items-start space-x-3 cursor-pointer p-3 rounded-lg border hover:bg-muted/50">
                          <RadioGroupItem value="both" className="mt-1" />
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <Activity className="h-4 w-4 text-green-600" />
                              <span className="font-medium">Both Methods</span>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              Compare results from both NLP and LLM extraction. Useful for validation and testing.
                            </p>
                          </div>
                        </Label>
                      </div>
                    </RadioGroup>
                  </div>
                  
                  <div className="rounded-lg bg-muted/50 p-4">
                    <p className="text-sm text-muted-foreground">
                      <strong>Current selection:</strong> {extractionMode === 'nlp' ? 'NLP Pattern Matching' : extractionMode === 'llm' ? 'LLM Analysis' : 'Both Methods'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      This setting will be used for all subsequent analyses until changed.
                    </p>
                  </div>
                </CardContent>
              </>
            )}
          </Card>

          {/* Connecting line */}
          {expandedSection !== "results" && (
            <div className="flex justify-center">
              <div className="w-0.5 h-12 bg-border"></div>
            </div>
          )}

          {/* Hidden file input - always in DOM */}
          <input
            ref={fileInputRef}
            id="csv-file"
            type="file"
            accept=".csv"
            onChange={handleFileUpload}
            className="hidden"
            style={{ display: 'none' }}
          />
          
          {/* CSV Upload Section */}
          <Card className={`shadow-soft transition-all duration-300 ${
            expandedSection === "csv-upload" ? "shadow-soft-lg" : ""
          }`}>
            <CardHeader 
              className="cursor-pointer"
              onClick={() => toggleSection("csv-upload")}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-secondary rounded-md">
                    <Upload className="h-5 w-5 text-secondary-foreground" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Batch Processing</CardTitle>
                    <CardDescription>
                      Upload CSV with multiple patients - Click to expand
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {showValidator && (
                    <Badge variant="outline" className="animate-pulse">
                      Validating CSV...
                    </Badge>
                  )}
                  {expandedSection === "csv-upload" ? (
                    <ChevronUp className="h-5 w-5 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>
              </div>
            </CardHeader>
            
            {expandedSection === "csv-upload" && (
              <>
                <Separator />
                <CardContent className="space-y-6 pt-6">
                  {!showValidator ? (
                    <div className="space-y-4">
                      <div className="border-2 border-dashed border-muted rounded-lg p-8 text-center">
                        <FileSpreadsheet className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                        <Label htmlFor="csv-file" className="text-base font-medium block mb-2">
                          Select CSV File
                        </Label>
                        <p className="text-sm text-muted-foreground mb-4">
                          CSV should contain patient data with clinical notes
                        </p>
                        <Button 
                          onClick={() => fileInputRef.current?.click()}
                          disabled={isProcessing}
                          variant="outline"
                          size="lg"
                        >
                          <Upload className="mr-2 h-4 w-4" />
                          Choose CSV File
                        </Button>
                      </div>

                      {uploadedPatients.length > 0 && (
                        <div className="space-y-3">
                          <div className="flex justify-between items-center">
                            <h3 className="text-base font-medium">
                              Uploaded Patients
                            </h3>
                            <Badge variant="secondary">
                              {uploadedPatients.length} patients
                            </Badge>
                          </div>
                          
                          <div className="space-y-2 max-h-80 overflow-y-auto border rounded-lg p-2">
                            {uploadedPatients.map((patient) => (
                              <div 
                                key={patient.id} 
                                className="flex justify-between items-center p-3 rounded-md hover:bg-muted/50 transition-colors"
                              >
                                <div className="flex items-center gap-3">
                                  <User className="h-4 w-4 text-muted-foreground" />
                                  <div>
                                    <p className="font-medium text-sm">{patient.id}</p>
                                    {patient.data?.baseline_date && (
                                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                                        <Calendar className="h-3 w-3" />
                                        {new Date(patient.data.baseline_date).toLocaleDateString()}
                                      </p>
                                    )}
                                  </div>
                                </div>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => processPatient(patient)}
                                  disabled={isProcessing}
                                >
                                  Process
                                  <ChevronRight className="ml-1 h-3 w-3" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div>
                      <CSVValidator 
                        csvData={csvData} 
                        onValidationComplete={handleValidationComplete}
                        isUploading={isProcessing}
                      />
                      <Button 
                        onClick={() => {
                          setShowValidator(false);
                          setCsvData([]);
                        }}
                        variant="outline"
                        className="mt-4 w-full"
                      >
                        Cancel
                      </Button>
                    </div>
                  )}
                </CardContent>
              </>
            )}
          </Card>

          {/* Connecting line */}
          {(expandedSection === "new-analysis" || expandedSection === "csv-upload") && (
            <div className="flex justify-center">
              <div className="w-0.5 h-12 bg-border"></div>
            </div>
          )}

          {/* Results Section */}
          <Card className={`shadow-soft transition-all duration-300 ${
            expandedSection === "results" ? "shadow-soft-lg" : ""
          } ${!activePatientId ? "opacity-50" : ""}`}>
            <CardHeader 
              className={activePatientId ? "cursor-pointer" : ""}
              onClick={() => activePatientId && toggleSection("results")}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-md ${
                    activePatientId ? "bg-primary" : "bg-muted"
                  }`}>
                    <Database className={`h-5 w-5 ${
                      activePatientId ? "text-primary-foreground" : "text-muted-foreground"
                    }`} />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Analysis Results</CardTitle>
                    <CardDescription>
                      {activePatientId ? "View BT-RADS classification flowchart" : "Select a patient to view results"}
                    </CardDescription>
                  </div>
                </div>
                {activePatientId && (
                  expandedSection === "results" ? (
                    <ChevronUp className="h-5 w-5 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-muted-foreground" />
                  )
                )}
              </div>
            </CardHeader>
            
            {expandedSection === "results" && activePatientId && (
              <>
                <Separator />
                <CardContent className="p-6">
                  <BTRADSDecisionFlow 
                    patientId={activePatientId}
                    autoStart={true}
                    onProcessingComplete={(result) => {
                      console.log("Processing complete:", result);
                      markPatientAsProcessed(activePatientId);
                    }}
                    onProcessNext={processNextPatient}
                    onProcessPrevious={processPreviousPatient}
                    hasNextPatient={!!findNextUnprocessedPatient(activePatientId)}
                    hasPreviousPatient={!!findPreviousUnprocessedPatient(activePatientId)}
                    remainingCount={allPatients.length - processedPatientIds.size}
                    completedCount={processedPatientIds.size}
                    extractionMode={extractionMode}
                  />
                </CardContent>
              </>
            )}
          </Card>
        </div>
      </main>
    </div>
  );
}