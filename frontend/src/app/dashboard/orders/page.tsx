"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import {
  ShoppingBag,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Plus,
  Eye,
  Filter
} from "lucide-react";

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
import { orderApi } from "@/lib/api/api-service";
import { Order, OrderStatus } from "@/lib/api/types";
import { formatPrice, formatDate } from "@/lib/utils";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogFooter
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { OrderViewModal } from "@/components/OrderViewModal";
import { Switch } from "@/components/ui/switch";

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

export default function OrdersPage() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [confirmingOrderId, setConfirmingOrderId] = useState<number | null>(null);
  const [estimatedTime, setEstimatedTime] = useState(30); // Default to 30 minutes
  const [viewingOrder, setViewingOrder] = useState<Order | null>(null);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [hideCanceledOrders, setHideCanceledOrders] = useState(false);

  useEffect(() => {
    fetchOrders();
  }, []);

  // Filter orders whenever the filter state or orders change
  useEffect(() => {
    if (hideCanceledOrders) {
      setFilteredOrders(orders.filter(order => order.status !== "cancelled"));
    } else {
      setFilteredOrders(orders);
    }
  }, [orders, hideCanceledOrders]);

  const fetchOrders = async () => {
    try {
      setIsLoading(true);
      const ordersData = await orderApi.getAll();
      setOrders(ordersData);
    } catch (error) {
      console.error("Error fetching orders:", error);
      toast.error("Failed to load orders");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateStatus = async (orderId: number, newStatus: OrderStatus) => {
    try {
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

  const openConfirmDialog = (orderId: number) => {
    setConfirmingOrderId(orderId);
    setEstimatedTime(30); // Reset to default
  };

  const openViewModal = (order: Order) => {
    setViewingOrder(order);
    setIsViewModalOpen(true);
  };

  const closeViewModal = () => {
    setIsViewModalOpen(false);
    setViewingOrder(null);
  };

  const handleConfirmWithTime = async () => {
    if (!confirmingOrderId) return;
    
    try {
      // Use the enhanced status endpoint to update both status and time in one call
      await orderApi.updateStatus(confirmingOrderId, "confirmed", estimatedTime);
      
      // Update orders state with both changes
      setOrders(prevOrders => 
        prevOrders.map(order => 
          order.id === confirmingOrderId ? { 
            ...order, 
            status: "confirmed",
            estimated_preparation_time: estimatedTime
          } : order
        )
      );
      
      toast.success(`Order #${confirmingOrderId} confirmed with ${estimatedTime} minute preparation time`);
      setConfirmingOrderId(null); // Close dialog
    } catch (error) {
      console.error("Error confirming order:", error);
      toast.error("Failed to confirm order");
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
          <Button onClick={() => router.push("/dashboard/orders/create")}>
            <Plus className="h-4 w-4 mr-2" />
            Create Order
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Orders</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Manage and track all customer orders
          </p>
        </div>
        <div className="flex gap-4 items-center">
          <div className="flex items-center gap-2">
            <Label htmlFor="hide-cancelled" className="text-sm cursor-pointer select-none">
              Hide cancelled orders
            </Label>
            <Switch 
              id="hide-cancelled" 
              checked={hideCanceledOrders}
              onCheckedChange={setHideCanceledOrders}
            />
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchOrders}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Button onClick={() => router.push("/dashboard/orders/create")}>
              <Plus className="h-4 w-4 mr-2" />
              Create Order
            </Button>
          </div>
        </div>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Order ID</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Items</TableHead>
              <TableHead>Total</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredOrders.map((order) => (
              <TableRow key={order.id}>
                <TableCell className="font-medium">#{order.id}</TableCell>
                <TableCell>
                  <div>
                    <div className="font-medium">{order.customer_name}</div>
                    <div className="text-sm text-gray-500">{formatPhoneNumber(order.customer_phone)}</div>
                  </div>
                </TableCell>
                <TableCell>
                  {order.order_items.map((item, index) => (
                    <div key={`${item.menu_item_id}-${index}`} className="text-sm">
                      {item.quantity}x {item.menu_item_name}
                    </div>
                  ))}
                </TableCell>
                <TableCell>{formatPrice(order.total_amount)}</TableCell>
                <TableCell>{formatDate(new Date(order.created_at))}</TableCell>
                <TableCell>{getStatusBadge(order.status)}</TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    {order.status === "pending" && (
                      <>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="h-8"
                          onClick={() => openConfirmDialog(order.id)}
                        >
                          <CheckCircle2 className="h-4 w-4 mr-1" />
                          Confirm
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="h-8 text-red-600 border-red-200"
                          onClick={() => handleUpdateStatus(order.id, "cancelled")}
                        >
                          <XCircle className="h-4 w-4 mr-1" />
                          Cancel
                        </Button>
                      </>
                    )}
                    {order.status === "confirmed" && (
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="h-8"
                        onClick={() => handleUpdateStatus(order.id, "preparing")}
                      >
                        Begin Prep
                      </Button>
                    )}
                    {order.status === "preparing" && (
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="h-8"
                        onClick={() => handleUpdateStatus(order.id, "ready")}
                      >
                        Mark Ready
                      </Button>
                    )}
                    {order.status === "ready" && (
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="h-8"
                        onClick={() => handleUpdateStatus(order.id, "delivered")}
                      >
                        Mark Delivered
                      </Button>
                    )}
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="h-8"
                      onClick={() => openViewModal(order)}
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      View
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Confirm Order Dialog */}
      <Dialog open={confirmingOrderId !== null} onOpenChange={(open) => !open && setConfirmingOrderId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Set Preparation Time</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <div className="space-y-2">
              <Label htmlFor="estimated-time">Estimated Preparation Time (minutes)</Label>
              <Input
                id="estimated-time"
                type="number"
                min="1"
                value={estimatedTime}
                onChange={(e) => setEstimatedTime(parseInt(e.target.value) || 30)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmingOrderId(null)}>Cancel</Button>
            <Button onClick={handleConfirmWithTime}>
              <Clock className="h-4 w-4 mr-2" />
              Confirm Order
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Order Modal */}
      {viewingOrder && (
        <OrderViewModal
          order={viewingOrder}
          isOpen={isViewModalOpen}
          onClose={closeViewModal}
        />
      )}
    </div>
  );
} 