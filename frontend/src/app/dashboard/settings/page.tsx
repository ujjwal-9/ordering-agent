"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Save, RefreshCw, Building, Phone, Mail, Clock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";

interface RestaurantSettings {
  name: string;
  address: string;
  phone: string;
  email: string;
  opening_hours: string;
  is_active: boolean;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<RestaurantSettings>({
    name: "",
    address: "",
    phone: "",
    email: "",
    opening_hours: "",
    is_active: true,
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        setIsLoading(true);
        
        // Mock data for demo purposes
        const mockSettings: RestaurantSettings = {
          name: "Tote AI Restaurant",
          address: "123 Main Street, Downtown, CA 94123",
          phone: "(555) 123-4567",
          email: "info@toteairestaurant.com",
          opening_hours: "Monday-Sunday: 11:00 AM - 10:00 PM",
          is_active: true,
        };
        
        // In a real application, you would fetch from API
        setSettings(mockSettings);
      } catch (error) {
        console.error("Error fetching restaurant settings:", error);
        toast.error("Failed to load restaurant settings");
      } finally {
        setIsLoading(false);
      }
    };

    fetchSettings();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setSettings(prev => ({ ...prev, [name]: value }));
  };

  const handleToggleActive = (value: boolean) => {
    setSettings(prev => ({ ...prev, is_active: value }));
  };

  const handleSaveSettings = () => {
    // In a real application, you would save to API
    toast.success("Restaurant settings saved successfully");
  };

  // Fallback for loading state
  if (isLoading) {
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
          <h1 className="text-3xl font-bold tracking-tight">Restaurant Settings</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Manage your restaurant information and settings
          </p>
        </div>
        <Button onClick={() => window.location.reload()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>General Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Restaurant Name</Label>
            <div className="flex items-center space-x-2">
              <Building className="h-4 w-4 text-gray-500" />
              <Input 
                id="name" 
                name="name" 
                value={settings.name} 
                onChange={handleChange} 
                placeholder="Restaurant Name"
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="address">Address</Label>
            <Textarea 
              id="address" 
              name="address" 
              value={settings.address} 
              onChange={handleChange} 
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
                  value={settings.phone} 
                  onChange={handleChange} 
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
                  value={settings.email} 
                  onChange={handleChange} 
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
                value={settings.opening_hours} 
                onChange={handleChange} 
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
              checked={settings.is_active}
              onCheckedChange={handleToggleActive}
            />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSaveSettings}>
          <Save className="h-4 w-4 mr-2" />
          Save Settings
        </Button>
      </div>
    </div>
  );
} 