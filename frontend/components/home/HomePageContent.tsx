"use client";

import { useEffect, useState } from "react";

import { HomeDashboard } from "@/components/home/HomeDashboard";
import { LandingPage } from "@/components/landing/LandingPage";
import { LoadingState } from "@/components/ui/StatePanels";
import { getCurrentUser } from "@/lib/api";

export function HomePageContent() {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    getCurrentUser().then((result) => setLoggedIn(Boolean(result.data)));
  }, []);

  if (loggedIn === null) {
    return (
      <div className="sl-container py-12">
        <LoadingState message="Loading..." />
      </div>
    );
  }

  if (loggedIn) {
    return (
      <div className="sl-container py-5 sm:py-6">
        <HomeDashboard />
      </div>
    );
  }

  return <LandingPage />;
}
