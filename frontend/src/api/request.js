import axios from 'axios'

const request = axios.create({
  baseURL: 'http://10.109.96.72:8000',
  timeout: 300000
})

request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    const publicUrls = ['/user/create_user', '/user/login_user', '/user/send_email_code', '/user/register_by_email', '/user/login_by_email']

    if (token && !publicUrls.includes(config.url)) {
      config.headers.token = token
    }

    return config
  },
  error => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      console.error('登录已过期，请重新登录')
    }

    return Promise.reject(error)
  }
)

export default request
