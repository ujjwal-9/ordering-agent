import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    // Get auth token from request cookies
    const token = request.cookies.get("auth_token")?.value || request.headers.get("authorization");
    const authHeader = token ? (token.startsWith("Bearer ") ? token : `Bearer ${token}`) : "";
    
    if (!authHeader) {
      return NextResponse.json(
        { detail: "Authentication required" },
        { status: 401 }
      );
    }

    // Use auth header from the request
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    // Log the API URL for debugging
    console.log(`Making request to: ${apiUrl}/admin/users`);
    
    const response = await fetch(`${apiUrl}/admin/users`, {
      headers: {
        Authorization: authHeader,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching users:", error);
    return NextResponse.json(
      { detail: "Failed to fetch users" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    // Get auth token from request cookies or authorization header
    const token = request.cookies.get("auth_token")?.value || request.headers.get("authorization");
    const authHeader = token ? (token.startsWith("Bearer ") ? token : `Bearer ${token}`) : "";
    
    if (!authHeader) {
      return NextResponse.json(
        { detail: "Authentication required" },
        { status: 401 }
      );
    }

    const userData = await request.json();
    
    // Use auth header from the request
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    // Log the API URL for debugging
    console.log(`Making request to: ${apiUrl}/admin/users`);
    
    const response = await fetch(`${apiUrl}/admin/users`, {
      method: "POST",
      headers: {
        Authorization: authHeader,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error creating user:", error);
    return NextResponse.json(
      { detail: "Failed to create user" },
      { status: 500 }
    );
  }
} 