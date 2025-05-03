import axios from 'axios';
import { toast } from 'sonner';

// Define the API base URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Initialize auth header from localStorage on app load
if (typeof window !== 'undefined') {
  const token = localStorage.getItem('token');
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }
}

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`, config);
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data);
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear auth data on 401 errors
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      delete api.defaults.headers.common['Authorization'];
      
      // Redirect to login if not already there
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        toast.error('Session expired. Please login again.');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// User related API calls
export const authApi = {
  // Register a new user
  register: async (userData: any) => {
    try {
      const response = await api.post('/users/register', userData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Login user
  login: async (credentials: any) => {
    try {
      const response = await api.post('/users/login', credentials);
      if (response.data.access_token) {
        const token = response.data.access_token;
        localStorage.setItem('token', token);
        
        // Update axios default headers
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        
        if (response.data.user) {
          localStorage.setItem('user', JSON.stringify(response.data.user));
        }
      } else {
        console.error('Login successful but no access token received');
      }
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Logout user
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    delete api.defaults.headers.common['Authorization'];
  },

  // Check if user is authenticated
  isAuthenticated: () => {
    return !!localStorage.getItem('token');
  },
};

// Customer related API calls
export const customerApi = {
  // Get all customers
  getAll: async () => {
    try {
      const response = await api.get('/customers');
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get customer by ID
  getById: async (id: string | number) => {
    try {
      const response = await api.get(`/customers/${id}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get customer by phone
  getByPhone: async (phone: string) => {
    try {
      const response = await api.get(`/customers/phone/${phone}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Create a new customer
  create: async (customerData: any) => {
    try {
      const response = await api.post('/customers', customerData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Update a customer
  update: async (phone: string, customerData: any) => {
    try {
      const response = await api.put(`/customers/${phone}`, customerData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get customer order history
  getOrderHistory: async (phone: string) => {
    try {
      const response = await api.get(`/customers/${phone}/orders`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },
};

// Menu related API calls
export const menuApi = {
  // Get all menu items
  getAll: async (category?: string) => {
    try {
      const url = category ? `/menu?category=${category}` : '/menu';
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get menu item by ID
  getById: async (id: string | number) => {
    try {
      const response = await api.get(`/menu/${id}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Create a new menu item
  create: async (menuItemData: any) => {
    try {
      const response = await api.post('/menu', menuItemData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Update a menu item
  update: async (id: string | number, menuItemData: any) => {
    try {
      const response = await api.put(`/menu/${id}`, menuItemData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Delete a menu item
  delete: async (id: string | number) => {
    try {
      const response = await api.delete(`/menu/${id}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },
};

// Add-on related API calls
export const addOnApi = {
  // Get all add-ons
  getAll: async (category?: string) => {
    try {
      const url = category ? `/addons?category=${category}` : '/addons';
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get add-on by ID
  getById: async (id: string | number) => {
    try {
      const response = await api.get(`/addons/${id}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Create a new add-on
  create: async (addOnData: any) => {
    try {
      const response = await api.post('/addons', addOnData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Update an add-on
  update: async (id: string | number, addOnData: any) => {
    try {
      const response = await api.put(`/addons/${id}`, addOnData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Delete an add-on
  delete: async (id: string | number) => {
    try {
      const response = await api.delete(`/addons/${id}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },
};

// Normalize order payloads to ensure order_items is parsed as an array
const normalizeOrder = (order: any) => {
  // Ensure order_items is an array
  let items = order.order_items;
  if (typeof items === 'string') {
    try {
      items = JSON.parse(items);
    } catch {
      console.error('Failed to parse order_items JSON string:', items);
      items = [];
    }
  }
  if (!Array.isArray(items)) {
    items = [];
  }
  // Standardize each item
  const standardized = items.map((item: any) => {
    const menu_item_id = item.menu_item_id ?? item.id ?? null;
    const menu_item_name = item.menu_item_name ?? item.item_name ?? '';
    const quantity = item.quantity ?? 0;
    const base_price = item.base_price ?? item.price ?? 0;
    const total_price = item.total_price ?? quantity * base_price;
    const add_ons_raw = item.add_ons ?? [];
    const add_ons = add_ons_raw.map((ao: any) =>
      typeof ao === 'string'
        ? { add_on_id: null, add_on_name: ao, price: 0 }
        : {
            add_on_id: ao.add_on_id ?? ao.id ?? null,
            add_on_name: ao.add_on_name ?? ao.name ?? '',
            price: ao.price ?? 0,
          }
    );
    return { menu_item_id, menu_item_name, quantity, base_price, total_price, add_ons };
  });
  return { ...order, order_items: standardized };
};

// Order related API calls
export const orderApi = {
  // Get all orders
  getAll: async (status?: string) => {
    try {
      const url = status ? `/orders?status=${status}` : '/orders';
      const response = await api.get(url);
      const data = response.data;
      return Array.isArray(data) ? data.map(normalizeOrder) : [];
    } catch (error) {
      throw error;
    }
  },

  // Get order by ID
  getById: async (id: string | number) => {
    try {
      const response = await api.get(`/orders/${id}`);
      return normalizeOrder(response.data);
    } catch (error) {
      throw error;
    }
  },

  // Create a new order
  create: async (orderData: any) => {
    try {
      const response = await api.post('/orders', orderData);
      return normalizeOrder(response.data);
    } catch (error) {
      throw error;
    }
  },

  // Update order status
  updateStatus: async (id: string | number, status: string, estimatedTime?: number) => {
    try {
      const data: any = { status };
      if (estimatedTime !== undefined) {
        data.estimated_preparation_time = estimatedTime;
      }
      const response = await api.put(`/orders/${id}/status`, data);
      return normalizeOrder(response.data);
    } catch (error) {
      throw error;
    }
  },

  // Update estimated preparation time
  updateEstimatedTime: async (id: string | number, minutes: number) => {
    try {
      console.log(`Updating order ${id} estimated time to ${minutes} minutes`);
      
      // Try using the POST endpoint which accepts a different payload structure
      const response = await api.post(`/set-time/${id}`, { 
        minutes: minutes 
      });
      
      console.log('Update response:', response.data);
      
      return response.data;
    } catch (error) {
      console.error('Error updating estimated time:', error);
      throw error;
    }
  },
};

// Restaurant related API calls
export const restaurantApi = {
  // Get restaurant info
  getInfo: async () => {
    try {
      const response = await api.get('/restaurant');
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Update restaurant info
  update: async (id: string | number, restaurantData: any) => {
    try {
      const response = await api.put(`/restaurant/${id}`, restaurantData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },
}; 