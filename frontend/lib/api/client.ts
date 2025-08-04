import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add auth token if available
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const api = {
  patients: {
    list: async (params?: any) => {
      const { data } = await apiClient.get('/api/patients/', { params })
      return data
    },
    
    get: async (id: string) => {
      const { data } = await apiClient.get(`/api/patients/${id}`)
      return data
    },
    
    getById: async (id: string) => {
      const { data } = await apiClient.get(`/api/patients/${id}`)
      return data
    },
    
    create: async (patientData: any) => {
      const { data } = await apiClient.post('/api/patients/', patientData)
      return data
    },
    
    upload: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      
      // Use axios directly to avoid header conflicts
      const { data } = await axios.post(
        `${API_BASE_URL}/api/patients/upload`,
        formData,
        {
          headers: {
            // Let browser set Content-Type with boundary automatically
          }
        }
      );
      return data
    },
    
    startProcessing: async (id: string, autoValidate = false) => {
      const { data } = await apiClient.post(`/api/patients/${id}/process`, null, {
        params: { auto_validate: autoValidate }
      })
      return data
    },
    
    getStatus: async (id: string) => {
      const { data } = await apiClient.get(`/api/patients/${id}/status`)
      return data
    },
    
    getResult: async (id: string) => {
      const { data } = await apiClient.get(`/api/patients/${id}`)
      // Extract BT-RADS result if available
      if (data.btrads_result) {
        return typeof data.btrads_result === 'string' 
          ? JSON.parse(data.btrads_result) 
          : data.btrads_result
      }
      return null
    }
  },
  
  agents: {
    list: async () => {
      const { data } = await apiClient.get('/api/agents/list')
      return data
    },
    
    getResults: async (patientId: string, params?: any) => {
      const { data } = await apiClient.get(`/api/agents/results/${patientId}`, { params })
      return data
    },
    
    test: async (agentId: string, testData: any) => {
      const { data } = await apiClient.post(`/api/agents/test/${agentId}`, testData)
      return data
    }
  },
  
  validation: {
    validate: async (request: any) => {
      const { data } = await apiClient.post('/api/validation/validate', request)
      return data
    },
    
    getPending: async (patientId: string) => {
      const { data } = await apiClient.get(`/api/validation/pending/${patientId}`)
      return data.pending_validations
    }
  },
  
  reports: {
    getSummary: async (patientId: string) => {
      const { data } = await apiClient.get(`/api/reports/${patientId}/summary`)
      return data
    },
    
    exportPDF: async (patientId: string) => {
      const response = await apiClient.get(`/api/reports/${patientId}/pdf`, {
        responseType: 'blob'
      })
      return response.data
    },
    
    exportJSON: async (patientId: string, includeRaw = false) => {
      const response = await apiClient.get(`/api/reports/${patientId}/export/json`, {
        params: { include_raw: includeRaw },
        responseType: 'blob'
      })
      return response.data
    },
    
    getAuditTrail: async (patientId: string) => {
      const { data } = await apiClient.get(`/api/reports/${patientId}/audit-trail`)
      return data.audit_trail
    }
  },
  
  llm: {
    extract: async (request: {
      clinical_note: string
      extraction_type: 'medications' | 'radiation_date'
      model?: string
    }) => {
      const { data } = await apiClient.post('/api/llm/extract', request)
      return data
    },
    
    getModels: async () => {
      const { data } = await apiClient.get('/api/llm/models')
      return data
    },
    
    checkStatus: async () => {
      const { data } = await apiClient.get('/api/llm/status')
      return data
    }
  },
  
  vllm: {
    extract: async (request: {
      clinical_note: string
      extraction_type: 'medications' | 'radiation_date'
      followup_date?: string
    }) => {
      const { data } = await apiClient.post('/api/vllm/extract', request)
      return data
    },
    
    checkStatus: async () => {
      const { data } = await apiClient.get('/api/vllm/status')
      return data
    }
  }
}

export default apiClient