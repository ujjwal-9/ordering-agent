"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Utensils, RefreshCw, Plus, Edit, X, Check, Trash2 } from "lucide-react";

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
import { formatPrice } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { menuApi, addOnApi } from "@/lib/api/api-service";
import { MenuItem, MenuItemCreate, MenuItemUpdate, AddOn, AddOnCreate, AddOnUpdate } from "@/lib/api/types";

export default function MenuPage() {
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [addOns, setAddOns] = useState<AddOn[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'items' | 'addons'>('items');
  
  // Menu Item Form State
  const [isMenuItemFormOpen, setIsMenuItemFormOpen] = useState(false);
  const [menuItemFormData, setMenuItemFormData] = useState<MenuItemCreate>({
    name: '',
    category: '',
    base_price: 0,
    description: '',
    is_available: true
  });
  const [editingMenuItemId, setEditingMenuItemId] = useState<number | null>(null);
  
  // Add-on Form State
  const [isAddOnFormOpen, setIsAddOnFormOpen] = useState(false);
  const [addOnFormData, setAddOnFormData] = useState<AddOnCreate>({
    name: '',
    category: '',
    price: 0,
    is_available: true
  });
  const [editingAddOnId, setEditingAddOnId] = useState<number | null>(null);
  
  // Delete Confirmation Dialog
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<{id: number, type: 'menuItem' | 'addOn'} | null>(null);

  useEffect(() => {
    fetchMenuData();
  }, []);

  const fetchMenuData = async () => {
    try {
      setIsLoading(true);
      
      // Fetch menu items and add-ons from API
      const [menuItemsData, addOnsData] = await Promise.all([
        menuApi.getAll(),
        addOnApi.getAll()
      ]);
      
      setMenuItems(menuItemsData);
      setAddOns(addOnsData);
    } catch (error) {
      console.error("Error fetching menu data:", error);
      toast.error("Failed to load menu data");
    } finally {
      setIsLoading(false);
    }
  };

  // Menu Item CRUD operations
  const handleCreateMenuItem = async () => {
    try {
      const newItem = await menuApi.create(menuItemFormData);
      setMenuItems(prev => [...prev, newItem]);
      toast.success("Menu item created successfully");
      setIsMenuItemFormOpen(false);
      resetMenuItemForm();
    } catch (error) {
      console.error("Error creating menu item:", error);
      toast.error("Failed to create menu item");
    }
  };

  const handleUpdateMenuItem = async () => {
    if (!editingMenuItemId) return;
    
    try {
      const updatedItem = await menuApi.update(editingMenuItemId, menuItemFormData);
      setMenuItems(prev => 
        prev.map(item => item.id === editingMenuItemId ? updatedItem : item)
      );
      toast.success("Menu item updated successfully");
      setIsMenuItemFormOpen(false);
      resetMenuItemForm();
    } catch (error) {
      console.error("Error updating menu item:", error);
      toast.error("Failed to update menu item");
    }
  };

  const handleDeleteMenuItem = async (id: number) => {
    try {
      await menuApi.delete(id);
      setMenuItems(prev => prev.filter(item => item.id !== id));
      toast.success("Menu item deleted successfully");
      setDeleteConfirmOpen(false);
      setItemToDelete(null);
    } catch (error) {
      console.error("Error deleting menu item:", error);
      toast.error("Failed to delete menu item");
    }
  };

  const toggleItemAvailability = async (id: number, currentStatus: boolean) => {
    try {
      const updatedItem = await menuApi.update(id, {
        is_available: !currentStatus
      });
      
      setMenuItems(prev => 
        prev.map(item => 
          item.id === id ? updatedItem : item
        )
      );
      toast.success("Item availability updated");
    } catch (error) {
      console.error("Error updating item availability:", error);
      toast.error("Failed to update item availability");
    }
  };

  // Add-on CRUD operations
  const handleCreateAddOn = async () => {
    try {
      const newAddOn = await addOnApi.create(addOnFormData);
      setAddOns(prev => [...prev, newAddOn]);
      toast.success("Add-on created successfully");
      setIsAddOnFormOpen(false);
      resetAddOnForm();
    } catch (error) {
      console.error("Error creating add-on:", error);
      toast.error("Failed to create add-on");
    }
  };

  const handleUpdateAddOn = async () => {
    if (!editingAddOnId) return;
    
    try {
      const updatedAddOn = await addOnApi.update(editingAddOnId, addOnFormData);
      setAddOns(prev => 
        prev.map(addon => addon.id === editingAddOnId ? updatedAddOn : addon)
      );
      toast.success("Add-on updated successfully");
      setIsAddOnFormOpen(false);
      resetAddOnForm();
    } catch (error) {
      console.error("Error updating add-on:", error);
      toast.error("Failed to update add-on");
    }
  };

  const handleDeleteAddOn = async (id: number) => {
    try {
      await addOnApi.delete(id);
      setAddOns(prev => prev.filter(addon => addon.id !== id));
      toast.success("Add-on deleted successfully");
      setDeleteConfirmOpen(false);
      setItemToDelete(null);
    } catch (error) {
      console.error("Error deleting add-on:", error);
      toast.error("Failed to delete add-on");
    }
  };

  const toggleAddonAvailability = async (id: number, currentStatus: boolean) => {
    try {
      const updatedAddOn = await addOnApi.update(id, {
        is_available: !currentStatus
      });
      
      setAddOns(prev => 
        prev.map(addon => 
          addon.id === id ? updatedAddOn : addon
        )
      );
      toast.success("Add-on availability updated");
    } catch (error) {
      console.error("Error updating add-on availability:", error);
      toast.error("Failed to update add-on availability");
    }
  };

  // Form Helpers
  const openMenuItemForm = (item?: MenuItem) => {
    if (item) {
      setMenuItemFormData({
        name: item.name,
        category: item.category,
        base_price: item.base_price,
        description: item.description || '',
        is_available: item.is_available
      });
      setEditingMenuItemId(item.id);
    } else {
      resetMenuItemForm();
    }
    setIsMenuItemFormOpen(true);
  };

  const resetMenuItemForm = () => {
    setMenuItemFormData({
      name: '',
      category: '',
      base_price: 0,
      description: '',
      is_available: true
    });
    setEditingMenuItemId(null);
  };

  const openAddOnForm = (addon?: AddOn) => {
    if (addon) {
      setAddOnFormData({
        name: addon.name,
        category: addon.category,
        price: addon.price,
        is_available: addon.is_available
      });
      setEditingAddOnId(addon.id);
    } else {
      resetAddOnForm();
    }
    setIsAddOnFormOpen(true);
  };

  const resetAddOnForm = () => {
    setAddOnFormData({
      name: '',
      category: '',
      price: 0,
      is_available: true
    });
    setEditingAddOnId(null);
  };

  const confirmDelete = (id: number, type: 'menuItem' | 'addOn') => {
    setItemToDelete({ id, type });
    setDeleteConfirmOpen(true);
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
          <h1 className="text-3xl font-bold tracking-tight">Menu Management</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Manage your restaurant menu and add-ons
          </p>
        </div>
        <Button onClick={fetchMenuData}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="flex space-x-4 border-b pb-2">
        <Button 
          variant={activeTab === 'items' ? 'default' : 'outline'} 
          onClick={() => setActiveTab('items')}
        >
          Menu Items
        </Button>
        <Button 
          variant={activeTab === 'addons' ? 'default' : 'outline'} 
          onClick={() => setActiveTab('addons')}
        >
          Add-ons
        </Button>
      </div>

      {activeTab === 'items' && (
        <div className="space-y-4">
          <div className="flex justify-between">
            <h2 className="text-lg font-medium">Menu Items</h2>
            <Button size="sm" onClick={() => openMenuItemForm()}>
              <Plus className="h-4 w-4 mr-1" />
              Add Item
            </Button>
          </div>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {menuItems.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                      No menu items found. Add your first menu item to get started.
                    </TableCell>
                  </TableRow>
                ) : (
                  menuItems.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">#{item.id}</TableCell>
                      <TableCell>{item.name}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">{item.category}</Badge>
                      </TableCell>
                      <TableCell>{formatPrice(item.base_price)}</TableCell>
                      <TableCell className="max-w-xs truncate">{item.description}</TableCell>
                      <TableCell>
                        {item.is_available ? (
                          <Badge className="bg-green-50 text-green-600 border-green-200">Available</Badge>
                        ) : (
                          <Badge variant="outline" className="text-red-600">Unavailable</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex space-x-2">
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-8 w-8 p-0"
                            onClick={() => openMenuItemForm(item)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className={`h-8 w-8 p-0 ${item.is_available ? 'text-red-600' : 'text-green-600'}`}
                            onClick={() => toggleItemAvailability(item.id, item.is_available)}
                          >
                            {item.is_available ? <X className="h-4 w-4" /> : <Check className="h-4 w-4" />}
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-8 w-8 p-0 text-red-600"
                            onClick={() => confirmDelete(item.id, 'menuItem')}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {activeTab === 'addons' && (
        <div className="space-y-4">
          <div className="flex justify-between">
            <h2 className="text-lg font-medium">Add-ons</h2>
            <Button size="sm" onClick={() => openAddOnForm()}>
              <Plus className="h-4 w-4 mr-1" />
              Add New
            </Button>
          </div>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {addOns.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                      No add-ons found. Add your first add-on to get started.
                    </TableCell>
                  </TableRow>
                ) : (
                  addOns.map((addon) => (
                    <TableRow key={addon.id}>
                      <TableCell className="font-medium">#{addon.id}</TableCell>
                      <TableCell>{addon.name}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">{addon.category}</Badge>
                      </TableCell>
                      <TableCell>{formatPrice(addon.price)}</TableCell>
                      <TableCell>
                        {addon.is_available ? (
                          <Badge className="bg-green-50 text-green-600 border-green-200">Available</Badge>
                        ) : (
                          <Badge variant="outline" className="text-red-600">Unavailable</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex space-x-2">
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-8 w-8 p-0"
                            onClick={() => openAddOnForm(addon)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className={`h-8 w-8 p-0 ${addon.is_available ? 'text-red-600' : 'text-green-600'}`}
                            onClick={() => toggleAddonAvailability(addon.id, addon.is_available)}
                          >
                            {addon.is_available ? <X className="h-4 w-4" /> : <Check className="h-4 w-4" />}
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-8 w-8 p-0 text-red-600"
                            onClick={() => confirmDelete(addon.id, 'addOn')}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* Menu Item Form */}
      <Sheet open={isMenuItemFormOpen} onOpenChange={setIsMenuItemFormOpen}>
        <SheetContent className="sm:max-w-md">
          <SheetHeader>
            <SheetTitle>{editingMenuItemId ? 'Edit Menu Item' : 'Add Menu Item'}</SheetTitle>
            <SheetDescription>
              {editingMenuItemId 
                ? 'Update the details of an existing menu item.' 
                : 'Add a new item to your restaurant menu.'}
            </SheetDescription>
          </SheetHeader>
          <div className="py-4 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input 
                id="name"
                value={menuItemFormData.name}
                onChange={(e) => setMenuItemFormData({...menuItemFormData, name: e.target.value})}
                placeholder="Cheeseburger"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Input 
                id="category"
                value={menuItemFormData.category}
                onChange={(e) => setMenuItemFormData({...menuItemFormData, category: e.target.value})}
                placeholder="burger, pizza, etc."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="base_price">Price</Label>
              <Input 
                id="base_price"
                type="number"
                step="0.01"
                value={menuItemFormData.base_price}
                onChange={(e) => setMenuItemFormData({...menuItemFormData, base_price: parseFloat(e.target.value)})}
                placeholder="9.99"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea 
                id="description"
                value={menuItemFormData.description}
                onChange={(e) => setMenuItemFormData({...menuItemFormData, description: e.target.value})}
                placeholder="Delicious burger with cheese..."
                rows={3}
              />
            </div>
            <div className="flex items-center space-x-2 pt-2">
              <Switch
                id="is_available"
                checked={menuItemFormData.is_available}
                onCheckedChange={(checked) => setMenuItemFormData({...menuItemFormData, is_available: checked})}
              />
              <Label htmlFor="is_available">Available</Label>
            </div>
          </div>
          <SheetFooter>
            <Button type="button" variant="outline" onClick={() => setIsMenuItemFormOpen(false)}>
              Cancel
            </Button>
            <Button 
              type="button" 
              onClick={editingMenuItemId ? handleUpdateMenuItem : handleCreateMenuItem}
            >
              {editingMenuItemId ? 'Update' : 'Create'}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Add-on Form */}
      <Sheet open={isAddOnFormOpen} onOpenChange={setIsAddOnFormOpen}>
        <SheetContent className="sm:max-w-md">
          <SheetHeader>
            <SheetTitle>{editingAddOnId ? 'Edit Add-on' : 'Add New Add-on'}</SheetTitle>
            <SheetDescription>
              {editingAddOnId 
                ? 'Update the details of an existing add-on.' 
                : 'Add a new add-on option to your menu.'}
            </SheetDescription>
          </SheetHeader>
          <div className="py-4 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="addon-name">Name</Label>
              <Input 
                id="addon-name"
                value={addOnFormData.name}
                onChange={(e) => setAddOnFormData({...addOnFormData, name: e.target.value})}
                placeholder="Extra Cheese"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="addon-category">Category</Label>
              <Input 
                id="addon-category"
                value={addOnFormData.category}
                onChange={(e) => setAddOnFormData({...addOnFormData, category: e.target.value})}
                placeholder="burger, pizza, etc."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="addon-price">Price</Label>
              <Input 
                id="addon-price"
                type="number"
                step="0.01"
                value={addOnFormData.price}
                onChange={(e) => setAddOnFormData({...addOnFormData, price: parseFloat(e.target.value)})}
                placeholder="1.50"
              />
            </div>
            <div className="flex items-center space-x-2 pt-2">
              <Switch
                id="addon-is_available"
                checked={addOnFormData.is_available}
                onCheckedChange={(checked) => setAddOnFormData({...addOnFormData, is_available: checked})}
              />
              <Label htmlFor="addon-is_available">Available</Label>
            </div>
          </div>
          <SheetFooter>
            <Button type="button" variant="outline" onClick={() => setIsAddOnFormOpen(false)}>
              Cancel
            </Button>
            <Button 
              type="button" 
              onClick={editingAddOnId ? handleUpdateAddOn : handleCreateAddOn}
            >
              {editingAddOnId ? 'Update' : 'Create'}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Deletion</DialogTitle>
          </DialogHeader>
          <p>
            Are you sure you want to delete this {itemToDelete?.type === 'menuItem' ? 'menu item' : 'add-on'}? 
            This action cannot be undone.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmOpen(false)}>
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={() => {
                if (itemToDelete) {
                  if (itemToDelete.type === 'menuItem') {
                    handleDeleteMenuItem(itemToDelete.id);
                  } else {
                    handleDeleteAddOn(itemToDelete.id);
                  }
                }
              }}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
} 