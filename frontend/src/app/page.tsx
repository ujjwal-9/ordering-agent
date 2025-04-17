"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, useScroll, useTransform, useInView } from "framer-motion";
import { 
  ChevronRight, 
  Utensils, 
  Phone, 
  Clock, 
  ShoppingBag, 
  User,
  ArrowRight,
  Mail
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { 
  fadeIn, 
  slideIn, 
  staggerContainer,
  textVariant
} from "@/lib/animations";

// Mock features
const features = [
  {
    icon: <ShoppingBag className="h-8 w-8 text-primary" />,
    title: "Order Management",
    description: "Effortlessly track and manage orders from receipt to delivery in real-time."
  },
  {
    icon: <Utensils className="h-8 w-8 text-primary" />,
    title: "Menu Customization",
    description: "Easily update your menu items, categories, and add-ons anytime."
  },
  {
    icon: <User className="h-8 w-8 text-primary" />,
    title: "Customer Profiles",
    description: "Build customer relationships with detailed profiles and order history."
  },
  {
    icon: <Clock className="h-8 w-8 text-primary" />,
    title: "Real-time Updates",
    description: "Keep your kitchen and customers informed with instant status updates."
  }
];

export default function LandingPage() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false });
  
  const { scrollYProgress } = useScroll();
  const y = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden bg-gray-950 text-white">
        <div className="absolute inset-0 z-0">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent to-gray-950 z-10" />
          <div className="absolute inset-0 bg-gradient-to-r from-gray-950/60 to-transparent z-10" />
          <div className="absolute inset-0 bg-[url('/hero-bg.jpg')] bg-cover bg-center opacity-40" />
        </div>
        
        <motion.div 
          variants={staggerContainer()}
          initial="hidden"
          animate="show"
          className="container mx-auto px-4 z-10 text-center"
        >
          <motion.h1 
            variants={textVariant(0.3)}
            className="text-4xl md:text-6xl font-bold mb-6"
          >
            Smart Ordering System for Modern Restaurants
          </motion.h1>
          
          <motion.p 
            variants={textVariant(0.5)}
            className="text-xl md:text-2xl mb-10 max-w-3xl mx-auto text-gray-200"
          >
            Streamline your restaurant operations with our comprehensive ordering and management platform.
          </motion.p>
          
          <motion.div 
            variants={fadeIn("up", 0.7)}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <Link href="/register">
              <Button 
                size="lg" 
                className="px-8 py-6 text-lg rounded-full"
              >
                Get Started <ChevronRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link href="/login">
              <Button 
                variant="outline" 
                size="lg" 
                className="px-8 py-6 text-lg rounded-full bg-transparent border-white text-white hover:bg-white hover:text-gray-950 border-2"
              >
                Login
              </Button>
            </Link>
          </motion.div>
        </motion.div>
        
        <motion.div 
          className="absolute bottom-10 w-full flex justify-center"
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          <ArrowRight className="h-8 w-8 rotate-90" />
        </motion.div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <motion.h2 
              ref={ref}
              variants={fadeIn("up", 0.2)}
              initial="hidden"
              animate={isInView ? "show" : "hidden"}
              className="text-3xl md:text-4xl font-bold mb-4"
            >
              Powerful Features for Your Restaurant
            </motion.h2>
            <motion.p 
              variants={fadeIn("up", 0.3)}
              initial="hidden"
              animate={isInView ? "show" : "hidden"}
              className="text-xl text-gray-600 max-w-3xl mx-auto"
            >
              Everything you need to manage orders, customers, and menu items efficiently.
            </motion.p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                variants={fadeIn("up", 0.2 + index * 0.1)}
                initial="hidden"
                whileInView="show"
                viewport={{ once: false, amount: 0.25 }}
                className="bg-gray-50 p-8 rounded-lg hover:shadow-lg transition-shadow"
              >
                <div className="mb-4">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
      
      {/* CTA Section */}
      <section className="py-20 bg-primary text-white">
        <div className="container mx-auto px-4 text-center">
          <motion.div
            variants={staggerContainer()}
            initial="hidden"
            whileInView="show"
            viewport={{ once: false, amount: 0.25 }}
          >
            <motion.h2 
              variants={textVariant(0.2)}
              className="text-3xl md:text-4xl font-bold mb-6"
            >
              Ready to Transform Your Restaurant Operations?
            </motion.h2>
            
            <motion.p 
              variants={textVariant(0.4)}
              className="text-xl mb-10 max-w-3xl mx-auto text-primary-foreground"
            >
              Join hundreds of restaurants already using our platform to streamline their ordering process.
            </motion.p>
            
            <motion.div variants={fadeIn("up", 0.6)}>
              <Link href="/register">
                <Button 
                  size="lg" 
                  className="px-8 py-6 text-lg rounded-full bg-white text-primary hover:bg-gray-100"
                >
                  Start Your Free Trial <ChevronRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            </motion.div>
          </motion.div>
        </div>
      </section>
      
      {/* Footer */}
      <footer className="bg-gray-950 text-white py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-xl font-bold mb-4">Ordering System</h3>
              <p className="text-gray-400">
                Streamlining restaurant operations with smart ordering solutions.
              </p>
            </div>
            
            <div>
              <h4 className="text-lg font-bold mb-4">Quick Links</h4>
              <ul className="space-y-2">
                <li><Link href="/" className="text-gray-400 hover:text-white transition-colors">Home</Link></li>
                <li><Link href="/login" className="text-gray-400 hover:text-white transition-colors">Login</Link></li>
                <li><Link href="/register" className="text-gray-400 hover:text-white transition-colors">Register</Link></li>
              </ul>
            </div>
            
            <div>
              <h4 className="text-lg font-bold mb-4">Features</h4>
              <ul className="space-y-2">
                <li><span className="text-gray-400">Order Management</span></li>
                <li><span className="text-gray-400">Menu Customization</span></li>
                <li><span className="text-gray-400">Customer Profiles</span></li>
                <li><span className="text-gray-400">Analytics</span></li>
              </ul>
            </div>
            
            <div>
              <h4 className="text-lg font-bold mb-4">Contact</h4>
              <ul className="space-y-2">
                <li className="flex items-center text-gray-400"><Phone className="h-4 w-4 mr-2" /> +1 (555) 123-4567</li>
                <li className="flex items-center text-gray-400"><Mail className="h-4 w-4 mr-2" /> support@orderingsystem.com</li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-gray-800 mt-10 pt-6 text-center text-gray-500">
            <p>© {new Date().getFullYear()} Ordering System. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
