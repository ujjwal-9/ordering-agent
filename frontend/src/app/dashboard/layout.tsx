"use client";

import React, { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { 
  Home, 
  ShoppingBag, 
  User, 
  Menu as MenuIcon, 
  Package, 
  Settings, 
  LogOut,
  X
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { useAuth } from "@/lib/auth-provider";
import { slideIn } from "@/lib/animations";

interface DashboardLayoutProps {
  children: ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const router = useRouter();
  const { isAuthenticated, logout, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: <Home className="mr-2 h-4 w-4" /> },
    { name: "Orders", href: "/dashboard/orders", icon: <ShoppingBag className="mr-2 h-4 w-4" /> },
    { name: "Customers", href: "/dashboard/customers", icon: <User className="mr-2 h-4 w-4" /> },
    { name: "Menu Items", href: "/dashboard/menu", icon: <MenuIcon className="mr-2 h-4 w-4" /> },
    { name: "Add-ons", href: "/dashboard/addons", icon: <Package className="mr-2 h-4 w-4" /> },
    { name: "Settings", href: "/dashboard/settings", icon: <Settings className="mr-2 h-4 w-4" /> },
  ];

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Desktop Sidebar */}
      <motion.aside
        variants={slideIn("left", "spring")}
        initial="hidden"
        animate="show"
        className="hidden md:flex md:w-64 md:flex-col"
      >
        <div className="flex flex-col flex-grow pt-5 overflow-y-auto border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-800">
          <div className="flex items-center flex-shrink-0 px-4">
            <h1 className="text-xl font-bold">Ordering System</h1>
          </div>
          <div className="mt-5 flex-1 flex flex-col">
            <nav className="flex-1 px-2 pb-4 space-y-1">
              {navItems.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className="group flex items-center px-2 py-2 text-sm font-medium rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  {item.icon}
                  {item.name}
                </Link>
              ))}
              <button
                onClick={handleLogout}
                className="w-full group flex items-center px-2 py-2 text-sm font-medium rounded-md text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 mt-4"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </button>
            </nav>
          </div>
        </div>
      </motion.aside>

      {/* Mobile Sidebar */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-10 flex items-center justify-between p-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <h1 className="text-lg font-bold">Ordering System</h1>
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="outline" size="icon">
              <MenuIcon className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-[240px] sm:w-[300px]">
            <div className="flex flex-col h-full">
              <div className="flex items-center justify-between py-2">
                <h2 className="text-lg font-bold">Menu</h2>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <X className="h-4 w-4" />
                  </Button>
                </SheetTrigger>
              </div>
              <nav className="flex-1 mt-4 space-y-1">
                {navItems.map((item) => (
                  <Link
                    key={item.name}
                    href={item.href}
                    className="flex items-center px-2 py-2 text-sm font-medium rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    {item.icon}
                    {item.name}
                  </Link>
                ))}
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center px-2 py-2 text-sm font-medium rounded-md text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 mt-4"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </button>
              </nav>
            </div>
          </SheetContent>
        </Sheet>
      </div>

      {/* Main Content */}
      <main className="flex-1 pt-16 md:pt-0">
        <div className="py-6 max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
          {children}
        </div>
      </main>
    </div>
  );
} 