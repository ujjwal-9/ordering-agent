"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { 
  ShoppingBag, 
  Users, 
  Utensils, 
  DollarSign,
  ArrowRight,
  Clock,
  CheckCircle2,
  XCircle,
  Filter,
} from "lucide-react";
import { toast } from "sonner";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { orderApi } from "@/lib/api/api-service";
import { fadeIn, staggerContainer } from "@/lib/animations";
import { formatPrice, formatDate } from "@/lib/utils";
import { Order, OrderStatus } from "@/lib/api/types";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

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

export default function DashboardPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hideCanceledOrders, setHideCanceledOrders] = useState(false);
  const [stats, setStats] = useState({
    totalOrders: 0,
    pendingOrders: 0,
    totalCustomers: 0,
    totalRevenue: 0,
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        
        // Fetch actual order data from API
        const ordersData = await orderApi.getAll();
        
        setOrders(ordersData);
        
        // Calculate stats from orders
        setStats({
          totalOrders: ordersData.length,
          pendingOrders: ordersData.filter((order: Order) => order.status === 'pending').length,
          totalCustomers: new Set(ordersData.map((order: Order) => order.customer_phone)).size,
          totalRevenue: ordersData.reduce((sum: number, order: Order) => sum + order.total_amount, 0),
        });
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
        toast.error("Failed to load dashboard data");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Filter orders whenever the filter state or orders change
  useEffect(() => {
    if (hideCanceledOrders) {
      setFilteredOrders(orders.filter(order => order.status !== "cancelled"));
    } else {
      setFilteredOrders(orders);
    }
  }, [orders, hideCanceledOrders]);

  const handleUpdateStatus = async (orderId: number, newStatus: OrderStatus) => {
    try {
      // Update order status via API
      await orderApi.updateStatus(orderId, newStatus);
      
      // Update orders state
      setOrders(prevOrders => 
        prevOrders.map(order => 
          order.id === orderId ? { ...order, status: newStatus } : order
        )
      );
      
      toast.success(`Order #${orderId} updated to ${newStatus}`);
    } catch (error) {
      console.error("Error updating order status:", error);
      toast.error("Failed to update order status");
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
  if (!filteredOrders || filteredOrders.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-100px)]">
        <ShoppingBag className="h-16 w-16 text-gray-400 mb-4" />
        <h2 className="text-2xl font-bold mb-2">
          {orders.length > 0 && hideCanceledOrders 
            ? "No non-cancelled orders found" 
            : "No orders yet"}
        </h2>
        <p className="text-gray-500 mb-4">
          {orders.length > 0 && hideCanceledOrders
            ? "All existing orders have been cancelled. Adjust the filter to see cancelled orders."
            : "Your orders will appear here once customers place them."}
        </p>
        <div className="flex gap-2 items-center">
          {orders.length > 0 && hideCanceledOrders && (
            <Button variant="outline" onClick={() => setHideCanceledOrders(false)}>
              <Filter className="h-4 w-4 mr-2" />
              Show All Orders
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <motion.div
      variants={staggerContainer()}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Overview of your restaurant operations
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <motion.div variants={fadeIn("up", 0.1)}>
          <Card>
            <CardHeader className="pb-2 space-y-0 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium">Total Orders</CardTitle>
              <ShoppingBag className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalOrders}</div>
              <p className="text-xs text-gray-500">+{Math.floor(Math.random() * 15) + 1}% from last week</p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeIn("up", 0.2)}>
          <Card>
            <CardHeader className="pb-2 space-y-0 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium">Pending Orders</CardTitle>
              <Clock className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.pendingOrders}</div>
              <p className="text-xs text-gray-500">Need attention</p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeIn("up", 0.3)}>
          <Card>
            <CardHeader className="pb-2 space-y-0 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium">Total Customers</CardTitle>
              <Users className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalCustomers}</div>
              <p className="text-xs text-gray-500">+{Math.floor(Math.random() * 10) + 1}% from last month</p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeIn("up", 0.4)}>
          <Card>
            <CardHeader className="pb-2 space-y-0 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
              <DollarSign className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatPrice(stats.totalRevenue)}</div>
              <p className="text-xs text-gray-500">+{Math.floor(Math.random() * 20) + 5}% from last month</p>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Recent Orders */}
      <motion.div variants={fadeIn("up", 0.5)}>
        <Card className="col-span-4">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Orders</CardTitle>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Label htmlFor="hide-cancelled-dash" className="text-sm cursor-pointer select-none">
                  Hide cancelled orders
                </Label>
                <Switch 
                  id="hide-cancelled-dash" 
                  checked={hideCanceledOrders}
                  onCheckedChange={setHideCanceledOrders}
                />
              </div>
              <Link href="/dashboard/orders">
                <Button variant="ghost" size="sm" className="gap-1">
                  View all <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Order ID
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Customer
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Amount
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredOrders.map((order) => (
                    <tr key={order.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        #{order.id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {order.customer_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(new Date(order.created_at))}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatPrice(order.total_amount)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          order.status === 'delivered' ? 'bg-green-100 text-green-800' :
                          order.status === 'preparing' ? 'bg-blue-100 text-blue-800' :
                          order.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {order.status.charAt(0).toUpperCase() + order.status.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        {order.status === 'pending' && (
                          <div className="flex justify-end gap-2">
                            <Button 
                              onClick={() => handleUpdateStatus(order.id, 'confirmed')}
                              variant="outline" 
                              size="sm"
                              className="h-8 w-8 p-0 text-green-600"
                            >
                              <CheckCircle2 className="h-4 w-4" />
                            </Button>
                            <Button 
                              onClick={() => handleUpdateStatus(order.id, 'cancelled' as OrderStatus)}
                              variant="outline" 
                              size="sm"
                              className="h-8 w-8 p-0 text-red-600"
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </div>
                        )}
                        {order.status !== 'pending' && (
                          <Link href={`/dashboard/orders/${order.id}`}>
                            <Button variant="outline" size="sm">
                              Details
                            </Button>
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
} 