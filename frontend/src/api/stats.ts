import apiClient from './client'
import type { AdminStats } from '@/types/api'

export const statsApi = {
  overview(timeRange: string = '24h') {
    return apiClient.get<AdminStats>('/admin/stats', {
      params: { time_range: timeRange }
    })
  },
}
