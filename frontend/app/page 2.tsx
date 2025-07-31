"use client";

import { useState, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { 
  FileText, 
  Upload, 
  Brain, 
  AlertCircle, 
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  User,
  Calendar,
  Activity
} from "lucide-react";
import { BTRADSFlowChart } from "@/components/graph/BTRADSFlowChart";
import { PatientData } from "@/types/patient";
import { api } from "@/lib/api/client";

export default function Home() {
  const [activePatientId, setActivePatientId] = useState<string | null>(null);
  const [clinicalNote, setClinicalNote] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedPatients, setUploadedPatients] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async () => {
    if (!clinicalNote.trim()) return;

    setIsProcessing(true);
    setError(null);
    setSuccess(null);
    
    try {
      // Create patient with clinical note
      const patientData: Partial<PatientData> = {
        clinical_note: clinicalNote,
        baseline_date: new Date().toISOString().split('T')[0],
        followup_date: new Date().toISOString().split('T')[0],
      };

      const patient = await api.patients.create(patientData);
      setActivePatientId(patient.id);
      
      // Start processing
      await api.patients.startProcessing(patient.id, false);
      setSuccess("Analysis started successfully. Navigate to the Results tab to view progress.");
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

    setIsProcessing(true);
    setError(null);
    setSuccess(null);
    
    try {
      const patients = await api.patients.upload(file);
      setUploadedPatients(patients);
      setSuccess(`Successfully uploaded ${patients.length} patients from CSV file.`);
    } catch (error) {
      console.error("Error uploading file:", error);
      setError("Failed to upload CSV file. Please check the format and try again.");
    } finally {
      setIsProcessing(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const processPatient = async (patient: any) => {
    setActivePatientId(patient.id);
    setIsProcessing(true);
    setError(null);
    
    try {
      await api.patients.startProcessing(patient.id, false);
      setSuccess(`Started processing patient ${patient.id}`);
    } catch (error) {
      console.error("Error processing patient:", error);
      setError(`Failed to process patient ${patient.id}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      {/* Header */}
      <div className="border-b bg-white/50 dark:bg-slate-900/50 backdrop-blur">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <Brain className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            <div>
              <h1 className="text-2xl font-bold">BT-RADS Multi-Agent System</h1>
              <p className="text-sm text-muted-foreground">
                AI-powered brain tumor imaging analysis
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto p-6 max-w-7xl">
        {/* Alerts */}
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        
        {success && (
          <Alert className="mb-4 border-green-200 bg-green-50 dark:bg-green-950/20">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800 dark:text-green-200">
              {success}
            </AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue="new" className="space-y-6">
          <TabsList className="grid w-full max-w-md grid-cols-3">
            <TabsTrigger value="new" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              New Analysis
            </TabsTrigger>
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload className="h-4 w-4" />
              CSV Upload
            </TabsTrigger>
            <TabsTrigger value="results" disabled={!activePatientId} className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Results
            </TabsTrigger>
          </TabsList>

          <TabsContent value="new" className="space-y-4">
            <Card className="shadow-lg">
              <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20">
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-blue-600" />
                  Clinical Note Analysis
                </CardTitle>
                <CardDescription>
                  Enter a clinical note or radiology report for instant BT-RADS classification
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6 pt-6">
                <div className="space-y-2">
                  <Label htmlFor="clinical-note" className="text-base font-medium">
                    Clinical Note / Radiology Report
                  </Label>
                  <Textarea
                    id="clinical-note"
                    placeholder="Paste the clinical note or radiology report here for analysis..."
                    className="min-h-[350px] resize-none font-mono text-sm"
                    value={clinicalNote}
                    onChange={(e) => setClinicalNote(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    The AI will extract key information and classify according to BT-RADS criteria
                  </p>
                </div>
                
                <Separator />
                
                <Button 
                  onClick={handleSubmit}
                  disabled={isProcessing || !clinicalNote.trim()}
                  className="w-full h-12 text-base"
                  size="lg"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Brain className="mr-2 h-5 w-5" />
                      Analyze with BT-RADS
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Info Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="bg-blue-50/50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-blue-600" />
                    Real-time Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Multi-agent system processes notes in real-time with visual feedback
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-green-50/50 dark:bg-green-950/20 border-green-200 dark:border-green-800">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Activity className="h-4 w-4 text-green-600" />
                    Interactive Validation
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Review and validate AI extractions at each decision point
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-purple-50/50 dark:bg-purple-950/20 border-purple-200 dark:border-purple-800">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <FileSpreadsheet className="h-4 w-4 text-purple-600" />
                    Export Reports
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Generate comprehensive PDF reports with full algorithm path
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="upload" className="space-y-4">
            <Card className="shadow-lg">
              <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20">
                <CardTitle className="flex items-center gap-2">
                  <FileSpreadsheet className="h-5 w-5 text-green-600" />
                  Batch CSV Upload
                </CardTitle>
                <CardDescription>
                  Process multiple patients at once by uploading a properly formatted CSV file
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6 pt-6">
                <div className="space-y-4">
                  <div className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-8 text-center">
                    <FileSpreadsheet className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <Label htmlFor="csv-file" className="text-base font-medium block mb-2">
                      Select CSV File
                    </Label>
                    <p className="text-sm text-muted-foreground mb-4">
                      CSV should contain patient data with clinical notes and measurements
                    </p>
                    <input
                      ref={fileInputRef}
                      id="csv-file"
                      type="file"
                      accept=".csv"
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                    <Button 
                      onClick={() => fileInputRef.current?.click()}
                      disabled={isProcessing}
                      variant="outline"
                      size="lg"
                      className="mx-auto"
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      Choose CSV File
                    </Button>
                  </div>

                  {/* CSV Format Guide */}
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      <strong>Required CSV columns:</strong> patient_id, clinical_note, baseline_date, followup_date
                      <br />
                      <strong>Optional columns:</strong> radiation_date, volume measurements, ground_truth_btrads
                    </AlertDescription>
                  </Alert>
                </div>
                
                {uploadedPatients.length > 0 && (
                  <>
                    <Separator />
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <h3 className="text-lg font-semibold">
                          Uploaded Patients ({uploadedPatients.length})
                        </h3>
                        <Badge variant="secondary">
                          Ready to Process
                        </Badge>
                      </div>
                      
                      <div className="space-y-2 max-h-80 overflow-y-auto border rounded-lg p-2">
                        {uploadedPatients.map((patient, index) => (
                          <div 
                            key={patient.id} 
                            className="flex justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                          >
                            <div className="flex items-center gap-3">
                              <User className="h-5 w-5 text-gray-400" />
                              <div>
                                <p className="font-medium">{patient.id}</p>
                                <p className="text-sm text-muted-foreground">
                                  {patient.data?.baseline_date && (
                                    <span className="flex items-center gap-1">
                                      <Calendar className="h-3 w-3" />
                                      {new Date(patient.data.baseline_date).toLocaleDateString()}
                                    </span>
                                  )}
                                </p>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              onClick={() => processPatient(patient)}
                              disabled={isProcessing}
                            >
                              {isProcessing ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                "Process"
                              )}
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="results" className="space-y-4">
            <Card className="shadow-lg">
              <CardHeader>
                <CardTitle>BT-RADS Analysis Results</CardTitle>
                <CardDescription>
                  Interactive flowchart showing the algorithm path and decision points
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {activePatientId && (
                  <div className="h-[600px]">
                    <BTRADSFlowChart 
                      patientId={activePatientId}
                      onNodeClick={(nodeId) => console.log("Node clicked:", nodeId)}
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}