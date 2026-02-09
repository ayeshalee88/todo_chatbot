import NextAuth, { AuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";

export const authOptions: AuthOptions = {
  // Removed Prisma adapter to avoid database sync issues between backend and frontend
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
          response_type: "code"
        }
      },
      async profile(profile) {
        // After Google authenticates the user, call our backend to get/create user and tokens
        try {
          const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          const response = await fetch(`${BACKEND_API_URL}/api/google-signin`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              email: profile.email,
              name: profile.name,
              google_id: profile.sub,
            }),
          });

          if (!response.ok) {
            console.error("Google sign-in to backend failed:", response.status);
            // Return a default user object instead of null
            return {
              id: profile.sub,
              name: profile.name,
              email: profile.email,
              image: profile.picture,
            };
          }

          const userData = await response.json();
          console.log("Successfully authenticated Google user:", userData.email);

          // Return standard user data for the session (tokens will be handled in jwt callback)
          return {
            id: userData.id || userData.user_id,
            name: userData.name || profile.name,
            email: userData.email || profile.email,
            image: profile.picture,
          };
        } catch (error) {
          console.error("Error during Google sign-in to backend:", error);
          // Return a default user object instead of null
          return {
            id: profile.sub,
            name: profile.name,
            email: profile.email,
            image: profile.picture,
          };
        }
      },
    }),
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          console.error("Missing email or password in credentials");
          return null;
        }

        try {
          // Authenticate against the backend API
          const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          console.log(`Attempting to authenticate user: ${credentials.email} at ${BACKEND_API_URL}/api/login`);
          const response = await fetch(`${BACKEND_API_URL}/api/login`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          });

          console.log(`Backend response status: ${response.status}`);

          if (!response.ok) {
            const errorData = await response.text(); // Get the error response
            console.error("Backend authentication failed:", errorData);
            return null;
          }

          const userData = await response.json();
          console.log("Successfully authenticated user:", userData.email);

          // Return user data for the session, including the access and refresh tokens
          return {
            id: userData.id || userData.user_id,
            email: userData.email,
            name: userData.name || userData.email.split('@')[0],
            accessToken: userData.access_token,
            refreshToken: userData.refresh_token,
          };
        } catch (error) {
          console.error("Authentication error:", error);
          return null;
        }
      },
    }),
  ],

  session: {
    strategy: "jwt",
  },

  callbacks: {
    async signIn({ user, account, profile }) {
      // Handle the token exchange after successful sign-in with Google
      if (account?.provider === 'google' && profile) {
        try {
          const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          const response = await fetch(`${BACKEND_API_URL}/api/google-signin`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              email: profile.email,
              name: profile.name,
              google_id: (profile as any).sub,
            }),
          });

          if (response.ok) {
            const userData = await response.json();
            
            // Store tokens in user object temporarily
            (user as any).accessToken = userData.access_token;
            (user as any).refreshToken = userData.refresh_token;
          } else {
            console.error("Google sign-in to backend failed:", response.status);
            return false; // Deny sign-in
          }
        } catch (error) {
          console.error("Error during Google sign-in to backend:", error);
          return false; // Deny sign-in
        }
      }
      
      return true; // Allow sign-in
    },
    async jwt({ token, user, account }) {
      if (user) {
        // Add user info to the JWT token
        token.id = user.id;
        token.email = user.email;
        token.name = user.name;
        
        // Add tokens from the user object (set in signIn callback for Google, or in authorize for Credentials)
        if ((user as any).accessToken) {
          token.accessToken = (user as any).accessToken;
          token.refreshToken = (user as any).refreshToken;
          // Set access token expiry to 14 minutes (just before backend token expires at 15 mins)
          token.accessTokenExpires = Date.now() + 14 * 60 * 1000;
        }
      }

      // If token is expired, try to refresh it
      if (Date.now() >= (token.accessTokenExpires as number || 0)) {
        console.log("Access token expired, attempting refresh");
        return await refreshAccessToken(token);
      }

      return token;
    },
    async session({ session, token }) {
      // Add the access token to the session object
      session.user = {
        ...session.user,
        id: token.id as string,
        email: token.email as string,
        name: token.name as string,
      };
      if (token.accessToken) {
        session.accessToken = token.accessToken as string;
      }
      if (token.refreshToken) {
        // Optionally include refresh token in session if needed (but usually not recommended for security)
      }
      return session;
    },
  },

  pages: {
    signIn: "/login",
    error: "/login",
  },

  secret: process.env.NEXTAUTH_SECRET,
  debug: process.env.NODE_ENV === "development",
};

// Function to refresh access token
async function refreshAccessToken(token: any) {
  try {
    // Use the same API URL that was used for login
    const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    
    // Add timeout handling and better error reporting
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    const response = await fetch(`${BACKEND_API_URL}/api/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        refresh_token: token.refreshToken,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      console.error("Token refresh failed:", response.status, await response.text().catch(() => ''));
      // Return the token as-is, which will cause the user to be logged out
      return {
        ...token,
        error: "RefreshAccessTokenError",
      };
    }

    const refreshedTokens = await response.json();

    return {
      ...token,
      accessToken: refreshedTokens.access_token,
      accessTokenExpires: Date.now() + 14 * 60 * 1000, // 14 minutes from now
    };
  } catch (error: any) {
    console.error("Error during token refresh:", error);
    
    // If it's a timeout or network error, return the old token to allow retry later
    if (error.name === 'AbortError' || error.code === 'UND_ERR_HEADERS_TIMEOUT') {
      console.warn("Token refresh timed out, keeping old token temporarily");
      // Extend the expiry time slightly to allow for retry
      return {
        ...token,
        accessTokenExpires: Date.now() + 5 * 60 * 1000, // 5 minutes from now
      };
    }
    
    return {
      ...token,
      error: "RefreshAccessTokenError",
    };
  }
}

export default NextAuth(authOptions);