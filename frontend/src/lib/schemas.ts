import * as z from "zod";

// User registration schema
export const registerSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters"),
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
});

// User login schema
export const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

// Customer schema
export const customerSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  phone: z.string().min(10, "Phone number must be at least 10 digits"),
  email: z.string().email("Please enter a valid email address").optional(),
  preferred_payment_method: z.string().optional(),
  dietary_preferences: z.string().optional(),
});

// Menu item schema
export const menuItemSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  category: z.string().min(1, "Category is required"),
  base_price: z.number().min(0, "Price must be a positive number"),
  description: z.string().optional(),
  is_available: z.boolean().default(true),
});

// Add-on schema
export const addOnSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  price: z.number().min(0, "Price must be a positive number"),
  category: z.string().min(1, "Category is required"),
  is_available: z.boolean().default(true),
});

// Order status options
export const orderStatusOptions = [
  "pending",
  "confirmed",
  "preparing",
  "ready",
  "delivered",
] as const;

// Order schema
export const orderSchema = z.object({
  customer_id: z.number().optional(),
  customer_name: z.string().min(2, "Customer name is required"),
  customer_phone: z.string().min(10, "Phone number must be at least 10 digits"),
  order_items: z.array(z.any()).min(1, "At least one item is required"),
  total_amount: z.number().min(0, "Total amount must be a positive number"),
  status: z.enum(orderStatusOptions).default("pending"),
  payment_method: z.string().optional(),
  special_instructions: z.string().optional(),
}); 