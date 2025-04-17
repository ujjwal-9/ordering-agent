import { NextRequest, NextResponse } from "next/server";

export async function GET(
  request: NextRequest,
  // context contains route params; use any to satisfy handler signature
  context: any
) {
  // Extract route params
  const params = await context.params;
  const userId = params.id;
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

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    // Log the API URL for debugging
    console.log(`Making request to: ${apiUrl}/admin/users/${userId}`);
    
    const response = await fetch(`${apiUrl}/admin/users/${userId}`, {
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
    console.error(`Error fetching user ${userId}:`, error);
    return NextResponse.json(
      { detail: "Failed to fetch user" },
      { status: 500 }
    );
  }
}

export async function PATCH(
  request: NextRequest,
  context: any
) {
  // Extract route params
  const params = await context.params;
  const userId = params.id;
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

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    // Log the API URL for debugging
    console.log(`Making request to: ${apiUrl}/admin/users/${userId}`);
    
    const response = await fetch(`${apiUrl}/admin/users/${userId}`, {
      method: "PATCH",
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
    console.error(`Error updating user ${userId}:`, error);
    return NextResponse.json(
      { detail: "Failed to update user" },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  // context contains route params; use any to satisfy handler signature
  context: any
) {
  // Extract route params
  const params = await context.params;
  const userId = params.id;
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

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    // Log the API URL for debugging
    console.log(`Making request to: ${apiUrl}/admin/users/${userId}`);
    
    const response = await fetch(`${apiUrl}/admin/users/${userId}`, {
      method: "DELETE",
      headers: {
        Authorization: authHeader,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(error, { status: response.status });
    }

    return new NextResponse(null, { status: 204 });
  } catch (error) {
    console.error(`Error deleting user ${userId}:`, error);
    return NextResponse.json(
      { detail: "Failed to delete user" },
      { status: 500 }
    );
  }
} 