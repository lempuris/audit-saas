import { SignedIn, SignedOut } from "@clerk/clerk-react";

import HomeScreen from "./screens/HomeScreen";
import SignInScreen from "./screens/SignInScreen";

export default function App() {
  return (
    <>
      <SignedOut>
        <SignInScreen />
      </SignedOut>
      <SignedIn>
        <HomeScreen />
      </SignedIn>
    </>
  );
}
