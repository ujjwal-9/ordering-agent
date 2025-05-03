"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import * as React from "react";
import {
  ShoppingBag,
  Clock,
  CheckCircle2,
  XCircle,
  ArrowLeft,
  UserCircle,
  Phone,
  Calendar,
  DollarSign,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { orderApi } from "@/lib/api/api-service";
import { formatPrice, formatDate } from "@/lib/utils";
import { Order, OrderStatus } from "@/lib/api/types";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

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

export default function OrderDetailsPage({ params }: any) {
  const router = useRouter();
  
  // Unwrap params using React.use() as recommended by Next.js
  // We need to cast both the input and output for type safety during the Next.js transition
  const unwrappedParams = React.use(params as any) as { id: string };
  const orderId = parseInt(unwrappedParams.id);
  const [order, setOrder] = useState<Order | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [estimatedTime, setEstimatedTime] = useState<number>(30); // Default to 30 minutes
  const [isConfirmingOrder, setIsConfirmingOrder] = useState(false);

  useEffect(() => {
    const fetchOrder = async () => {
      try {
        setIsLoading(true);
        
        // Fetch actual order data from the API
        const orderData = await orderApi.getById(orderId);
        
        if (!orderData) {
          toast.error("Order not found");
          router.push("/dashboard/orders");
          return;
        }
        
        setOrder(orderData);
        
        // If order already has an estimated preparation time, use it
        if (orderData.estimated_preparation_time) {
          setEstimatedTime(orderData.estimated_preparation_time);
        }
      } catch (error) {
        console.error("Error fetching order:", error);
        toast.error("Failed to load order details");
      } finally {
        setIsLoading(false);
      }
    };

    if (!isNaN(orderId)) {
      fetchOrder();
    } else {
      toast.error("Invalid order ID");
      router.push("/dashboard/orders");
    }
  }, [orderId, router]);

  const handleUpdateStatus = async (newStatus: OrderStatus) => {
    if (!order) return;
    
    try {
      // Use actual API to update order status
      await orderApi.updateStatus(order.id, newStatus);
      
      // Update order state
      setOrder({ ...order, status: newStatus });
      
      toast.success(`Order #${order.id} updated to ${newStatus}`);
    } catch (error) {
      console.error("Error updating order status:", error);
      toast.error("Failed to update order status");
    }
  };

  const handleConfirmWithTime = async () => {
    if (!order) return;
    
    try {
      setIsLoading(true);
      
      // Use the enhanced status endpoint to update both status and time in one call
      await orderApi.updateStatus(order.id, "confirmed", estimatedTime);
      
      // Update order state with both changes
      setOrder({ 
        ...order, 
        status: "confirmed", 
        estimated_preparation_time: estimatedTime 
      });
      
      // Reset confirmation mode
      setIsConfirmingOrder(false);
      
      toast.success(`Order #${order.id} confirmed with ${estimatedTime} minute preparation time`);
    } catch (error) {
      console.error("Error confirming order:", error);
      toast.error("Failed to confirm order");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateEstimatedTime = async () => {
    if (!order) return;
    
    try {
      // Update the estimated preparation time
      await orderApi.updateEstimatedTime(order.id, estimatedTime);
      
      // Update order state
      setOrder({ ...order, estimated_preparation_time: estimatedTime });
      
      toast.success(`Updated estimated preparation time to ${estimatedTime} minutes`);
    } catch (error) {
      console.error("Error updating estimated time:", error);
      toast.error("Failed to update estimated preparation time");
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-600 border-yellow-200">Pending</Badge>;
      case "confirmed":
        return <Badge variant="outline" className="bg-blue-50 text-blue-600 border-blue-200">Confirmed</Badge>;
      case "preparing":
        return <Badge variant="outline" className="bg-purple-50 text-purple-600 border-purple-200">Preparing</Badge>;
      case "ready":
        return <Badge variant="outline" className="bg-green-50 text-green-600 border-green-200">Ready</Badge>;
      case "delivered":
        return <Badge variant="outline" className="bg-gray-50 text-gray-600 border-gray-200">Delivered</Badge>;
      case "cancelled":
        return <Badge variant="outline" className="bg-red-50 text-red-600 border-red-200">Cancelled</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
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

  // Fallback if order not found
  if (!order) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-100px)]">
        <ShoppingBag className="h-16 w-16 text-gray-400 mb-4" />
        <h2 className="text-2xl font-bold mb-2">Order not found</h2>
        <p className="text-gray-500 mb-4">The order you're looking for doesn't exist.</p>
        <Button onClick={() => router.push("/dashboard/orders")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Orders
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-2">
        <Button 
          variant="outline" 
          onClick={() => router.push("/dashboard/orders")}
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Order #{order.id}</h1>
          <div className="flex items-center space-x-2 mt-1">
            <Clock className="h-4 w-4 text-gray-500" />
            <span className="text-gray-500">{formatDate(new Date(order.created_at))}</span>
            {getStatusBadge(order.status)}
            {order.estimated_preparation_time && (
              <span className="text-sm text-gray-500">
                <Clock className="h-3 w-3 inline mr-1" />
                Est. {order.estimated_preparation_time} min
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Order Items</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {order.order_items.map((item, i) => (
                <div key={i} className="flex flex-col">
                  <div className="flex justify-between text-sm">
                    <span>{item.quantity}x {item.menu_item_name}</span>
                    <span>{formatPrice(item.total_price)}</span>
                  </div>
                  {item.add_ons && item.add_ons.length > 0 && (
                    <div className="text-xs text-gray-500 ml-4">
                      + {item.add_ons.map(ao => ao.add_on_name).join(', ')}
                    </div>
                  )}
                </div>
              ))}
              
              <div className="pt-4 border-t mt-4">
                <div className="flex justify-between items-center">
                  <p className="font-bold">Total</p>
                  <p className="font-bold">{formatPrice(order.total_amount)}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Customer Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center space-x-2">
                  <UserCircle className="h-4 w-4 text-gray-500" />
                  <span>{order.customer_name}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Phone className="h-4 w-4 text-gray-500" />
                  <span>{formatPhoneNumber(order.customer_phone)}</span>
                </div>
                {order.estimated_preparation_time && (
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-gray-500" />
                    <span>Est. preparation time: {order.estimated_preparation_time} minutes</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Order Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {order.status === "pending" && !isConfirmingOrder && (
                <>
                  <Button 
                    className="w-full"
                    onClick={() => setIsConfirmingOrder(true)}
                  >
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Confirm Order
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full text-red-600"
                    onClick={() => handleUpdateStatus("cancelled")}
                  >
                    <XCircle className="h-4 w-4 mr-2" />
                    Cancel Order
                  </Button>
                </>
              )}
              
              {order.status === "pending" && isConfirmingOrder && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="confirm-estimated-time">Set Estimated Preparation Time (minutes)</Label>
                    <Input
                      id="confirm-estimated-time"
                      type="number"
                      min="1"
                      value={estimatedTime}
                      onChange={(e) => setEstimatedTime(parseInt(e.target.value) || 0)}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2 pt-2">
                    <Button 
                      variant="outline"
                      onClick={() => setIsConfirmingOrder(false)}
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleConfirmWithTime}
                    >
                      Confirm Order
                    </Button>
                  </div>
                </>
              )}
              
              {order.status === "confirmed" && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="estimated-time">Update Preparation Time (minutes)</Label>
                    <div className="flex space-x-2">
                      <Input
                        id="estimated-time"
                        type="number"
                        min="1"
                        value={estimatedTime}
                        onChange={(e) => setEstimatedTime(parseInt(e.target.value) || 0)}
                      />
                      <Button 
                        onClick={handleUpdateEstimatedTime}
                        variant="outline"
                      >
                        Update
                      </Button>
                    </div>
                  </div>
                  <div className="pt-2">
                    <Button 
                      className="w-full"
                      onClick={() => handleUpdateStatus("preparing")}
                    >
                      Begin Preparation
                    </Button>
                  </div>
                </>
              )}
              {order.status === "preparing" && (
                <Button 
                  className="w-full"
                  onClick={() => handleUpdateStatus("ready")}
                >
                  Mark as Ready
                </Button>
              )}
              {order.status === "ready" && (
                <Button 
                  className="w-full"
                  onClick={() => handleUpdateStatus("delivered")}
                >
                  Complete Order
                </Button>
              )}
              {(order.status === "delivered" || order.status === "cancelled") && (
                <div className="text-center py-2">
                  <p className="text-gray-500">This order is complete and cannot be modified.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
} 