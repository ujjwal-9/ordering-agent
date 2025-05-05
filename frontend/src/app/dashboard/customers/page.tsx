"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Users, RefreshCw, Phone, Mail, Utensils, Edit, Save } from "lucide-react";

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
import { customerApi } from "@/lib/api/api-service";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogFooter 
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

// Format phone number for display
const formatPhoneNumber = (phone: string) => {
  // Remove any non-digit characters
  const digits = phone.replace(/\D/g, '');
  
  // Format as XXX-XXX-XXXX if it has 10 digits
  if (digits.length === 10) {
    return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  
  // Return original if not 10 digits
  return phone;
};

interface Customer {
  id: number;
  name: string;
  phone: string;
  email: string;
  preferred_payment_method: string;
  total_orders: number;
  last_order_date?: string;
  created_at?: string;
  updated_at?: string;
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState({
    totalCustomers: 0,
    newCustomers: 0,
    returningCustomers: 0,
  });

  // Customer edit state
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [customerForm, setCustomerForm] = useState({
    name: "",
    phone: "",
    email: "",
    preferred_payment_method: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchCustomers = async () => {
    try {
      setIsLoading(true);
      
      // Fetch real customer data from API
      const customersData = await customerApi.getAll();
      
      setCustomers(customersData);
      
      // Calculate stats
      setStats({
        totalCustomers: customersData.length,
        newCustomers: customersData.filter((customer: Customer) => customer.total_orders === 0).length,
        returningCustomers: customersData.filter((customer: Customer) => customer.total_orders > 1).length,
      });
    } catch (error) {
      console.error("Error fetching customers:", error);
      toast.error("Failed to load customers");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, []);

  const handleEditClick = (customer: Customer) => {
    setEditingCustomer(customer);
    setCustomerForm({
      name: customer.name,
      phone: formatPhoneNumber(customer.phone),
      email: customer.email || "",
      preferred_payment_method: customer.preferred_payment_method || "",
    });
    setIsEditDialogOpen(true);
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    
    // Format phone number as user types
    if (name === "phone") {
      // Format as XXX-XXX-XXXX
      const digits = value.replace(/\D/g, "");
      let formattedPhone = "";
      
      if (digits.length <= 3) {
        formattedPhone = digits;
      } else if (digits.length <= 6) {
        formattedPhone = `${digits.slice(0, 3)}-${digits.slice(3)}`;
      } else {
        formattedPhone = `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
      }
      
      setCustomerForm({
        ...customerForm,
        phone: formattedPhone
      });
    } else {
      setCustomerForm({
        ...customerForm,
        [name]: value
      });
    }
  };

  const handleSaveCustomer = async () => {
    if (!editingCustomer) return;
    
    try {
      setIsSubmitting(true);
      
      // Remove formatting from phone number
      const phoneDigits = customerForm.phone.replace(/\D/g, "");
      
      // Verify we have at least name and phone
      if (!customerForm.name.trim()) {
        toast.error("Customer name is required");
        return;
      }
      
      if (phoneDigits.length < 10) {
        toast.error("Please enter a valid phone number (10 digits required)");
        return;
      }
      
      // Prepare data for API
      const customerData = {
        name: customerForm.name,
        phone: phoneDigits,
        email: customerForm.email || undefined,
        preferred_payment_method: customerForm.preferred_payment_method || undefined,
      };
      
      // Call API to update customer
      await customerApi.update(editingCustomer.phone, customerData);
      
      toast.success("Customer updated successfully");
      setIsEditDialogOpen(false);
      
      // Refresh the customer list
      fetchCustomers();
    } catch (error) {
      console.error("Error updating customer:", error);
      toast.error("Failed to update customer");
    } finally {
      setIsSubmitting(false);
    }
  };

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
        <Button onClick={fetchCustomers}>
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
                      {formatPhoneNumber(customer.phone)}
                    </div>
                    {customer.email && (
                      <div className="flex items-center text-sm">
                        <Mail className="h-3 w-3 mr-1 text-gray-500" />
                        {customer.email}
                      </div>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center">
                    <Utensils className="h-4 w-4 mr-1 text-gray-500" />
                    {customer.total_orders}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center justify-between">
                    {customer.preferred_payment_method ? (
                      <Badge variant="outline">{customer.preferred_payment_method}</Badge>
                    ) : (
                      <span className="text-gray-500">None</span>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleEditClick(customer)}
                      className="h-8 w-8 ml-2"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Edit Customer Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit Customer</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="name" className="text-right">
                Name
              </Label>
              <Input
                id="name"
                name="name"
                value={customerForm.name}
                onChange={handleFormChange}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="phone" className="text-right">
                Phone
              </Label>
              <Input
                id="phone"
                name="phone"
                value={customerForm.phone}
                onChange={handleFormChange}
                placeholder="XXX-XXX-XXXX"
                className="col-span-3"
                maxLength={12}
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="email" className="text-right">
                Email
              </Label>
              <Input
                id="email"
                name="email"
                type="email"
                value={customerForm.email}
                onChange={handleFormChange}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="payment" className="text-right">
                Payment
              </Label>
              <Input
                id="payment"
                name="preferred_payment_method"
                value={customerForm.preferred_payment_method}
                onChange={handleFormChange}
                placeholder="e.g. credit card, cash"
                className="col-span-3"
              />
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setIsEditDialogOpen(false)} variant="outline">
              Cancel
            </Button>
            <Button onClick={handleSaveCustomer} disabled={isSubmitting}>
              {isSubmitting ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                  Saving...
                </div>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
} 