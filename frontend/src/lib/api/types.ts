// User types
export interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
  is_admin?: boolean;
  is_active?: boolean;
}

export interface UserCredentials {
  email: string;
  password: string;
}

export interface UserRegistration extends UserCredentials {
  username: string;
  confirmPassword: string;
}

export interface AuthResponse {
  user: User;
  token: string;
}

// Customer types
export interface Customer {
  id: number;
  name: string;
  phone: string;
  email?: string;
  preferred_payment_method?: string;
  last_order_date?: string;
  total_orders: number;
  created_at: string;
  updated_at: string;
}

export interface CustomerCreate {
  name: string;
  phone: string;
  email?: string;
  preferred_payment_method?: string;
}

// Menu types
export interface MenuItem {
  id: number;
  name: string;
  category: string;
  base_price: number;
  description?: string;
  is_available: boolean;
  created_at: string;
  updated_at: string;
}

export interface MenuItemCreate {
  name: string;
  category: string;
  base_price: number;
  description?: string;
  is_available?: boolean;
}

export interface MenuItemUpdate {
  name?: string;
  category?: string;
  base_price?: number;
  description?: string;
  is_available?: boolean;
}

// Add-on types
export interface AddOn {
  id: number;
  name: string;
  price: number;
  category: string;
  type?: string;
  is_available: boolean;
  created_at: string;
  updated_at: string;
}

export interface AddOnCreate {
  name: string;
  price: number;
  category: string;
  type?: string;
  is_available?: boolean;
}

export interface AddOnUpdate {
  name?: string;
  price?: number;
  category?: string;
  type?: string;
  is_available?: boolean;
}

// Order types
export interface OrderItem {
  menu_item_id: number;
  menu_item_name: string;
  quantity: number;
  base_price: number;
  add_ons?: Array<{
    add_on_id: number;
    add_on_name: string;
    price: number;
  }>;
  total_price: number;
}

export type OrderStatus = 'pending' | 'confirmed' | 'preparing' | 'ready' | 'delivered' | 'cancelled';

export interface Order {
  id: number;
  customer_id?: number;
  customer_name: string;
  customer_phone: string;
  order_items: OrderItem[];
  total_amount: number;
  status: OrderStatus;
  estimated_preparation_time?: number;
  payment_method?: string;
  special_instructions?: string;
  created_at: string;
  updated_at: string;
}

export interface OrderCreate {
  customer_id?: number;
  customer_name: string;
  customer_phone: string;
  order_items: OrderItem[];
  total_amount: number;
  payment_method?: string;
  special_instructions?: string;
}

// Restaurant types
export interface Restaurant {
  id: number;
  name: string;
  address: string;
  phone: string;
  email?: string;
  opening_hours?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RestaurantUpdate {
  name?: string;
  address?: string;
  phone?: string;
  email?: string;
  opening_hours?: string;
  is_active?: boolean;
} 