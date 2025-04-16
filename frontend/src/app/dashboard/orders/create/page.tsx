"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ShoppingBag, Plus, Minus, X, Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";

import { orderApi, menuApi } from "@/lib/api/api-service";
import { formatPrice } from "@/lib/utils";
import { MenuItem, OrderCreate, OrderItem } from "@/lib/api/types";

export default function CreateOrderPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [selectedItems, setSelectedItems] = useState<OrderItem[]>([]);
  const [customerInfo, setCustomerInfo] = useState({
    name: "",
    phone: "",
  });
  const [specialInstructions, setSpecialInstructions] = useState("");
  const [submitLoading, setSubmitLoading] = useState(false);

  // Calculate total amount of order
  const totalAmount = selectedItems.reduce(
    (total, item) => total + item.total_price,
    0
  );

  useEffect(() => {
    const fetchMenuItems = async () => {
      try {
        setIsLoading(true);
        const items = await menuApi.getAll();
        // Filter out unavailable items
        const availableItems = items.filter(
          (item: MenuItem) => item.is_available
        );
        setMenuItems(availableItems);
      } catch (error) {
        console.error("Error fetching menu items:", error);
        toast.error("Failed to load menu items");
      } finally {
        setIsLoading(false);
      }
    };

    fetchMenuItems();
  }, []);

  const handleAddItem = (menuItem: MenuItem) => {
    // Check if item already in the order
    const existingItemIndex = selectedItems.findIndex(
      (item) => item.menu_item_id === menuItem.id
    );

    if (existingItemIndex !== -1) {
      // If item exists, increment quantity
      const updatedItems = [...selectedItems];
      updatedItems[existingItemIndex].quantity++;
      updatedItems[existingItemIndex].total_price =
        updatedItems[existingItemIndex].quantity *
        updatedItems[existingItemIndex].base_price;
      setSelectedItems(updatedItems);
    } else {
      // If item doesn't exist, add it
      const newItem: OrderItem = {
        menu_item_id: menuItem.id,
        menu_item_name: menuItem.name,
        quantity: 1,
        base_price: menuItem.base_price,
        total_price: menuItem.base_price,
      };
      setSelectedItems([...selectedItems, newItem]);
    }
  };

  const handleRemoveItem = (index: number) => {
    const updatedItems = [...selectedItems];
    updatedItems.splice(index, 1);
    setSelectedItems(updatedItems);
  };

  const handleUpdateQuantity = (index: number, quantity: number) => {
    if (quantity <= 0) {
      handleRemoveItem(index);
      return;
    }

    const updatedItems = [...selectedItems];
    updatedItems[index].quantity = quantity;
    updatedItems[index].total_price =
      quantity * updatedItems[index].base_price;
    setSelectedItems(updatedItems);
  };

  const handleCustomerInfoChange = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const { name, value } = e.target;
    
    if (name === "phone") {
      // Format phone number as user types (only allow digits)
      const formattedValue = value.replace(/\D/g, "");
      
      // Format as XXX-XXX-XXXX
      let formattedPhone = "";
      if (formattedValue.length <= 3) {
        formattedPhone = formattedValue;
      } else if (formattedValue.length <= 6) {
        formattedPhone = `${formattedValue.slice(0, 3)}-${formattedValue.slice(3)}`;
      } else {
        formattedPhone = `${formattedValue.slice(0, 3)}-${formattedValue.slice(3, 6)}-${formattedValue.slice(6, 10)}`;
      }
      
      setCustomerInfo({
        ...customerInfo,
        phone: formattedPhone,
      });
    } else {
      setCustomerInfo({
        ...customerInfo,
        [name]: value,
      });
    }
  };

  const validateOrderData = () => {
    if (!customerInfo.name.trim()) {
      toast.error("Customer name is required");
      return false;
    }

    // Validate phone number (must be in XXX-XXX-XXXX format or contain at least 10 digits)
    const phoneDigits = customerInfo.phone.replace(/\D/g, "");
    if (phoneDigits.length < 10) {
      toast.error("Please enter a valid phone number (10 digits required)");
      return false;
    }

    if (selectedItems.length === 0) {
      toast.error("Please add at least one item to the order");
      return false;
    }

    return true;
  };

  const handleCreateOrder = async () => {
    if (!validateOrderData()) return;

    try {
      setSubmitLoading(true);

      // Format phone number to just digits for backend
      const phoneDigits = customerInfo.phone.replace(/\D/g, "");

      const orderData: OrderCreate = {
        customer_name: customerInfo.name,
        customer_phone: phoneDigits,
        order_items: selectedItems,
        total_amount: totalAmount,
        special_instructions: specialInstructions || undefined,
      };

      const newOrder = await orderApi.create(orderData);
      toast.success("Order created successfully");
      router.push(`/dashboard/orders/${newOrder.id}`);
    } catch (error) {
      console.error("Error creating order:", error);
      toast.error("Failed to create order");
    } finally {
      setSubmitLoading(false);
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

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Create Order</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Add items to the order and provide customer information
          </p>
        </div>
        <Button onClick={() => router.push("/dashboard/orders")}>Cancel</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Menu Items</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {menuItems.map((menuItem) => (
                  <div
                    key={menuItem.id}
                    className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-medium">{menuItem.name}</h3>
                        <p className="text-sm text-gray-500 mb-2">
                          {formatPrice(menuItem.base_price)}
                        </p>
                        {menuItem.description && (
                          <p className="text-sm text-gray-600 line-clamp-2">
                            {menuItem.description}
                          </p>
                        )}
                      </div>
                      <Badge>{menuItem.category}</Badge>
                    </div>
                    <Button
                      className="w-full mt-3"
                      size="sm"
                      onClick={() => handleAddItem(menuItem)}
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Add
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Order Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="customerName">Customer Name</Label>
                  <Input
                    id="customerName"
                    name="name"
                    value={customerInfo.name}
                    onChange={handleCustomerInfoChange}
                    placeholder="Enter customer name"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="customerPhone">Customer Phone</Label>
                  <Input
                    id="customerPhone"
                    name="phone"
                    value={customerInfo.phone}
                    onChange={handleCustomerInfoChange}
                    placeholder="XXX-XXX-XXXX"
                    className="mt-1"
                    maxLength={12} // XXX-XXX-XXXX format
                  />
                  <p className="text-xs text-gray-500 mt-1">Format: XXX-XXX-XXXX</p>
                </div>
                <div>
                  <Label htmlFor="specialInstructions">
                    Special Instructions
                  </Label>
                  <Textarea
                    id="specialInstructions"
                    value={specialInstructions}
                    onChange={(e) => setSpecialInstructions(e.target.value)}
                    placeholder="Any special instructions"
                    className="mt-1"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Selected Items</CardTitle>
            </CardHeader>
            <CardContent>
              {selectedItems.length === 0 ? (
                <div className="text-center p-4 text-gray-500">
                  <ShoppingBag className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No items added yet</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {selectedItems.map((item, index) => (
                    <div key={`${item.menu_item_id}-${index}`}>
                      <div className="flex justify-between items-center">
                        <div className="flex-1">
                          <p className="font-medium">{item.menu_item_name}</p>
                          <p className="text-sm text-gray-500">
                            {formatPrice(item.base_price)} each
                          </p>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() =>
                              handleUpdateQuantity(index, item.quantity - 1)
                            }
                          >
                            <Minus className="h-4 w-4" />
                          </Button>
                          <span className="w-6 text-center">
                            {item.quantity}
                          </span>
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() =>
                              handleUpdateQuantity(index, item.quantity + 1)
                            }
                          >
                            <Plus className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8 text-red-500"
                            onClick={() => handleRemoveItem(index)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                      {index < selectedItems.length - 1 && (
                        <Separator className="my-2" />
                      )}
                    </div>
                  ))}

                  <div className="pt-4 border-t mt-4">
                    <div className="flex justify-between items-center font-bold">
                      <p>Total</p>
                      <p>{formatPrice(totalAmount)}</p>
                    </div>
                  </div>
                </div>
              )}

              <Button
                className="w-full mt-6"
                onClick={handleCreateOrder}
                disabled={selectedItems.length === 0 || submitLoading}
              >
                {submitLoading ? (
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                    Creating Order...
                  </div>
                ) : (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Create Order
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
} 