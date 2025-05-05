import React from "react";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { formatPrice, formatDate } from "@/lib/utils";
import { Order } from "@/lib/api/types";
import { Clock, UserCircle, Phone } from "lucide-react";

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

interface OrderViewModalProps {
  order: Order | null;
  isOpen: boolean;
  onClose: () => void;
}

export function OrderViewModal({ order, isOpen, onClose }: OrderViewModalProps) {
  if (!order) return null;

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

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>Order #{order.id}</span>
            {getStatusBadge(order.status)}
          </DialogTitle>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {/* Customer info */}
          <div className="space-y-2">
            <h3 className="font-medium">Customer Information</h3>
            <div className="text-sm space-y-1">
              <div className="flex items-center space-x-2">
                <UserCircle className="h-4 w-4 text-gray-500" />
                <span>{order.customer_name}</span>
              </div>
              <div className="flex items-center space-x-2">
                <Phone className="h-4 w-4 text-gray-500" />
                <span>{formatPhoneNumber(order.customer_phone)}</span>
              </div>
              <div className="flex items-center space-x-2">
                <Clock className="h-4 w-4 text-gray-500" />
                <span>{formatDate(new Date(order.created_at))}</span>
              </div>
              {order.estimated_preparation_time && (
                <div className="flex items-center space-x-2">
                  <Clock className="h-4 w-4 text-gray-500" />
                  <span>Est. preparation time: {order.estimated_preparation_time} min</span>
                </div>
              )}
            </div>
          </div>

          <Separator />

          {/* Order items */}
          <div className="space-y-2">
            <h3 className="font-medium">Order Items</h3>
            <div className="space-y-3">
              {order.order_items.map((item, index) => (
                <div key={`${item.menu_item_id}-${index}`} className="text-sm">
                  <div className="flex justify-between">
                    <div>
                      <p className="font-medium">{item.quantity}x {item.menu_item_name}</p>
                      <p className="text-xs text-gray-500">{formatPrice(item.base_price)} each</p>
                    </div>
                    <p className="font-medium">{formatPrice(item.total_price)}</p>
                  </div>
                  
                  {item.add_ons && item.add_ons.length > 0 && (
                    <div className="ml-4 mt-1">
                      <p className="text-xs text-gray-500 font-medium">Add-ons:</p>
                      <ul className="text-xs text-gray-500 pl-2">
                        {item.add_ons.map((addon, i) => (
                          <li key={i} className="flex justify-between">
                            <span>{addon.add_on_name}</span>
                            <span>{formatPrice(addon.price)}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {index < order.order_items.length - 1 && <Separator className="my-2" />}
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* Order total */}
          <div className="flex justify-between">
            <span className="font-bold">Total</span>
            <span className="font-bold">{formatPrice(order.total_amount)}</span>
          </div>

          {/* Special instructions */}
          {order.special_instructions && (
            <div className="mt-4 pt-4 border-t">
              <h3 className="font-medium text-sm">Special Instructions</h3>
              <p className="text-sm mt-1">{order.special_instructions}</p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 