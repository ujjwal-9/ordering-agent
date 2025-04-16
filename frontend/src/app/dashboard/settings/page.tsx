"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Save, RefreshCw, Building, Phone, Mail, Clock, User, Lock } from "lucide-react";
import axios from 'axios';

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/lib/auth-provider";

// Define the API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance with auth header
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

interface RestaurantSettings {
  id: number;
  name: string;
  address: string;
  phone: string;
  email: string;
  opening_hours: string;
  is_active: boolean;
}

interface UserSettings {
  username: string;
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export default function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.is_admin || false;
  
  const [restaurantSettings, setRestaurantSettings] = useState<RestaurantSettings>({
    id: 1,
    name: "",
    address: "",
    phone: "",
    email: "",
    opening_hours: "",
    is_active: true,
  });
  
  const [userSettings, setUserSettings] = useState<UserSettings>({
    username: user?.username || "",
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  
  const [isLoadingRestaurant, setIsLoadingRestaurant] = useState(true);

  useEffect(() => {
    const fetchRestaurantSettings = async () => {
      if (isAdmin) {
        try {
          setIsLoadingRestaurant(true);
          const response = await api.get('/restaurant');
          
          if (response.status === 200) {
            setRestaurantSettings(response.data);
          } else {
            toast.error("Failed to load restaurant settings");
          }
        } catch (error) {
          console.error("Error fetching restaurant settings:", error);
          toast.error("Failed to load restaurant settings");
        } finally {
          setIsLoadingRestaurant(false);
        }
      }
    };

    fetchRestaurantSettings();
    
    // Set username when user data is available
    if (user?.username) {
      setUserSettings(prev => ({
        ...prev,
        username: user.username
      }));
    }
  }, [isAdmin, user]);

  const handleRestaurantChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setRestaurantSettings(prev => ({ ...prev, [name]: value }));
  };

  const handleUserChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setUserSettings(prev => ({ ...prev, [name]: value }));
  };

  const handleToggleActive = (value: boolean) => {
    setRestaurantSettings(prev => ({ ...prev, is_active: value }));
  };

  const handleSaveRestaurantSettings = async () => {
    try {
      const response = await api.put(`/restaurant/${restaurantSettings.id}`, restaurantSettings);
      
      if (response.status === 200) {
        toast.success("Restaurant settings saved successfully");
      } else {
        toast.error("Failed to save restaurant settings");
      }
    } catch (error) {
      console.error("Error saving restaurant settings:", error);
      toast.error("Failed to save restaurant settings");
    }
  };

  const handleSaveUserSettings = async () => {
    // First validate passwords if changing password
    if (userSettings.newPassword) {
      if (userSettings.newPassword !== userSettings.confirmPassword) {
        toast.error("New passwords do not match");
        return;
      }
      
      if (!userSettings.currentPassword) {
        toast.error("Current password is required");
        return;
      }
    }
    
    // Update username if changed
    if (userSettings.username !== user?.username) {
      try {
        const response = await api.put('/users/me', { username: userSettings.username });
        
        if (response.status === 200) {
          toast.success("Username updated successfully");
          // Update auth context
          setTimeout(() => window.location.reload(), 1500);
        } else {
          toast.error("Failed to update username");
        }
      } catch (error) {
        console.error("Error updating username:", error);
        toast.error("Failed to update username");
      }
    }
    
    // Change password if provided
    if (userSettings.newPassword && userSettings.currentPassword) {
      try {
        const response = await api.post('/users/change-password', {
          current_password: userSettings.currentPassword,
          new_password: userSettings.newPassword
        });
        
        if (response.status === 200) {
          toast.success("Password changed successfully");
          // Clear password fields
          setUserSettings(prev => ({
            ...prev,
            currentPassword: "",
            newPassword: "",
            confirmPassword: ""
          }));
        } else {
          toast.error("Failed to change password");
        }
      } catch (error) {
        console.error("Error changing password:", error);
        toast.error("Failed to change password");
      }
    }
  };

  // Fallback for loading state
  if (isAdmin && isLoadingRestaurant) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-100px)]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Manage your account and application settings
          </p>
        </div>
        <Button onClick={() => window.location.reload()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <Tabs defaultValue="account">
        <TabsList className="mb-4">
          <TabsTrigger value="account">Account Settings</TabsTrigger>
          {isAdmin && <TabsTrigger value="restaurant">Restaurant Settings</TabsTrigger>}
        </TabsList>
        
        <TabsContent value="account">
          <Card>
            <CardHeader>
              <CardTitle>User Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">Username</Label>
                <div className="flex items-center space-x-2">
                  <User className="h-4 w-4 text-gray-500" />
                  <Input 
                    id="username" 
                    name="username" 
                    value={userSettings.username} 
                    onChange={handleUserChange} 
                    placeholder="Your username"
                  />
                </div>
              </div>
              
              <div className="pt-4 border-t">
                <h3 className="text-lg font-medium mb-2">Change Password</h3>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="currentPassword">Current Password</Label>
                    <div className="flex items-center space-x-2">
                      <Lock className="h-4 w-4 text-gray-500" />
                      <Input 
                        id="currentPassword" 
                        name="currentPassword" 
                        type="password"
                        value={userSettings.currentPassword} 
                        onChange={handleUserChange} 
                        placeholder="Enter your current password"
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="newPassword">New Password</Label>
                    <div className="flex items-center space-x-2">
                      <Lock className="h-4 w-4 text-gray-500" />
                      <Input 
                        id="newPassword" 
                        name="newPassword" 
                        type="password"
                        value={userSettings.newPassword} 
                        onChange={handleUserChange} 
                        placeholder="Enter new password"
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm New Password</Label>
                    <div className="flex items-center space-x-2">
                      <Lock className="h-4 w-4 text-gray-500" />
                      <Input 
                        id="confirmPassword" 
                        name="confirmPassword" 
                        type="password"
                        value={userSettings.confirmPassword} 
                        onChange={handleUserChange} 
                        placeholder="Confirm new password"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
          <div className="flex justify-end mt-4">
            <Button onClick={handleSaveUserSettings}>
              <Save className="h-4 w-4 mr-2" />
              Save Account Settings
            </Button>
          </div>
        </TabsContent>
        
        {isAdmin && (
          <TabsContent value="restaurant">
            <Card>
              <CardHeader>
                <CardTitle>Restaurant Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Restaurant Name</Label>
                  <div className="flex items-center space-x-2">
                    <Building className="h-4 w-4 text-gray-500" />
                    <Input 
                      id="name" 
                      name="name" 
                      value={restaurantSettings.name} 
                      onChange={handleRestaurantChange} 
                      placeholder="Restaurant Name"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="address">Address</Label>
                  <Textarea 
                    id="address" 
                    name="address" 
                    value={restaurantSettings.address} 
                    onChange={handleRestaurantChange} 
                    placeholder="Restaurant Address"
                    rows={2}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone Number</Label>
                    <div className="flex items-center space-x-2">
                      <Phone className="h-4 w-4 text-gray-500" />
                      <Input 
                        id="phone" 
                        name="phone" 
                        value={restaurantSettings.phone} 
                        onChange={handleRestaurantChange} 
                        placeholder="(555) 123-4567"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <div className="flex items-center space-x-2">
                      <Mail className="h-4 w-4 text-gray-500" />
                      <Input 
                        id="email" 
                        name="email" 
                        type="email"
                        value={restaurantSettings.email} 
                        onChange={handleRestaurantChange} 
                        placeholder="restaurant@example.com"
                      />
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="opening_hours">Opening Hours</Label>
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-gray-500" />
                    <Input 
                      id="opening_hours" 
                      name="opening_hours" 
                      value={restaurantSettings.opening_hours} 
                      onChange={handleRestaurantChange} 
                      placeholder="Monday-Sunday: 11:00 AM - 10:00 PM"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between space-x-2 pt-4">
                  <div>
                    <Label htmlFor="is_active" className="text-base">Restaurant Active Status</Label>
                    <p className="text-sm text-gray-500">
                      When turned off, customers won't be able to place orders
                    </p>
                  </div>
                  <Switch 
                    id="is_active"
                    checked={restaurantSettings.is_active}
                    onCheckedChange={handleToggleActive}
                  />
                </div>
              </CardContent>
            </Card>
            <div className="flex justify-end mt-4">
              <Button onClick={handleSaveRestaurantSettings}>
                <Save className="h-4 w-4 mr-2" />
                Save Restaurant Settings
              </Button>
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
} 