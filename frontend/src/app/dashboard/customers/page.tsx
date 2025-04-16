"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Users, RefreshCw, Phone, Mail, Utensils } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Customer {
  id: number;
  name: string;
  phone: string;
  email: string;
  preferred_payment_method: string;
  dietary_preferences: string;
  total_orders: number;
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState({
    totalCustomers: 0,
    newCustomers: 0,
    returningCustomers: 0,
  });

  useEffect(() => {
    const fetchCustomers = async () => {
      try {
        setIsLoading(true);
        
        // Mock data for demo purposes
        const mockCustomers: Customer[] = [
          {
            id: 1,
            name: "John Smith",
            phone: "555-1234-567",
            email: "john.smith@example.com",
            preferred_payment_method: "credit card",
            dietary_preferences: "no preferences",
            total_orders: 5,
          },
          {
            id: 2,
            name: "Emily Johnson",
            phone: "555-9876-543",
            email: "emily.j@example.com",
            preferred_payment_method: "cash",
            dietary_preferences: "vegetarian",
            total_orders: 3,
          },
          {
            id: 3,
            name: "Michael Brown",
            phone: "555-2223-333",
            email: "mbrown@example.com",
            preferred_payment_method: "digital payment",
            dietary_preferences: "gluten-free",
            total_orders: 7,
          },
          {
            id: 4,
            name: "Sarah Williams",
            phone: "555-4445-555",
            email: "sarahw@example.com",
            preferred_payment_method: "credit card",
            dietary_preferences: "dairy-free",
            total_orders: 2,
          },
          {
            id: 5,
            name: "David Miller",
            phone: "555-6667-777",
            email: "dmiller@example.com",
            preferred_payment_method: "cash",
            dietary_preferences: "no preferences",
            total_orders: 0,
          },
        ];
        
        // In a real application, you would fetch from API
        const customersData = mockCustomers;
        
        setCustomers(customersData);
        
        // Calculate stats
        setStats({
          totalCustomers: customersData.length,
          newCustomers: customersData.filter(customer => customer.total_orders === 0).length,
          returningCustomers: customersData.filter(customer => customer.total_orders > 1).length,
        });
      } catch (error) {
        console.error("Error fetching customers:", error);
        toast.error("Failed to load customers");
      } finally {
        setIsLoading(false);
      }
    };

    fetchCustomers();
  }, []);

  // Fallback for loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-100px)]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Fallback for empty state
  if (!customers || customers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-100px)]">
        <Users className="h-16 w-16 text-gray-400 mb-4" />
        <h2 className="text-2xl font-bold mb-2">No customers yet</h2>
        <p className="text-gray-500 mb-4">Your customer database will grow as people place orders.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Customers</h1>
          <p className="text-gray-500 dark:text-gray-400">
            View and manage your customer database
          </p>
        </div>
        <Button onClick={() => window.location.reload()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-6 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2 space-y-0 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">Total Customers</CardTitle>
            <Users className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalCustomers}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2 space-y-0 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">New Customers</CardTitle>
            <Users className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.newCustomers}</div>
            <p className="text-xs text-gray-500">Haven't placed an order yet</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2 space-y-0 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">Returning Customers</CardTitle>
            <Users className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.returningCustomers}</div>
            <p className="text-xs text-gray-500">Placed more than one order</p>
          </CardContent>
        </Card>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Contact</TableHead>
              <TableHead>Preferences</TableHead>
              <TableHead>Orders</TableHead>
              <TableHead>Payment</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers.map((customer) => (
              <TableRow key={customer.id}>
                <TableCell className="font-medium">#{customer.id}</TableCell>
                <TableCell>{customer.name}</TableCell>
                <TableCell>
                  <div className="flex flex-col space-y-1">
                    <div className="flex items-center text-sm">
                      <Phone className="h-3 w-3 mr-1 text-gray-500" />
                      {customer.phone}
                    </div>
                    <div className="flex items-center text-sm">
                      <Mail className="h-3 w-3 mr-1 text-gray-500" />
                      {customer.email}
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  {customer.dietary_preferences === "no preferences" ? (
                    <span className="text-gray-500">None</span>
                  ) : (
                    <Badge variant="outline">{customer.dietary_preferences}</Badge>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex items-center">
                    <Utensils className="h-4 w-4 mr-1 text-gray-500" />
                    {customer.total_orders}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="outline">{customer.preferred_payment_method}</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
} 