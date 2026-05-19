import axios from 'axios'
import { ElMessage } from 'element-plus'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const msg = error?.response?.data?.detail || error?.message || '网络异常'
    if (!axios.isCancel(error)) {
      ElMessage.error(`API: ${msg}`)
    }
    return Promise.reject(error)
  },
)
