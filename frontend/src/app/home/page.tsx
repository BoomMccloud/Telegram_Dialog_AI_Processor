'use client';

import { useEffect, useState } from 'react';
import AppLayout from '../AppLayout';

// Placeholder for dashboard data types
interface DashboardStats {
  totalProcessed: number;
  pendingApproval: number;
  approved: number;
  denied: number;
  averageProcessingTime: number;
}

export default function HomePage() {
  const [stats, setStats] = useState<DashboardStats>({
    totalProcessed: 0,
    pendingApproval: 0,
    approved: 0,
    denied: 0,
    averageProcessingTime: 0
  });
  const [loading, setLoading] = useState(true);

  // Placeholder for fetching dashboard data
  useEffect(() => {
    // This would be replaced with actual API call
    const fetchDashboardData = async () => {
      try {
        // Simulate API call with timeout
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Mock data for now
        setStats({
          totalProcessed: 152,
          pendingApproval: 24,
          approved: 112,
          denied: 16,
          averageProcessingTime: 3.2
        });
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <AppLayout>
      <div className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          
          {loading ? (
            <div className="mt-6 flex justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
            </div>
          ) : (
            <div className="mt-6">
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {/* Total Processed Card */}
                <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                  <div className="px-4 py-5 sm:p-6">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Total Processed
                    </dt>
                    <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
                      {stats.totalProcessed}
                    </dd>
                  </div>
                </div>

                {/* Pending Approval Card */}
                <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                  <div className="px-4 py-5 sm:p-6">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Pending Approval
                    </dt>
                    <dd className="mt-1 text-3xl font-semibold text-yellow-500 dark:text-yellow-400">
                      {stats.pendingApproval}
                    </dd>
                  </div>
                </div>

                {/* Approved Card */}
                <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                  <div className="px-4 py-5 sm:p-6">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Approved
                    </dt>
                    <dd className="mt-1 text-3xl font-semibold text-green-500 dark:text-green-400">
                      {stats.approved}
                    </dd>
                  </div>
                </div>

                {/* Denied Card */}
                <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                  <div className="px-4 py-5 sm:p-6">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Denied
                    </dt>
                    <dd className="mt-1 text-3xl font-semibold text-red-500 dark:text-red-400">
                      {stats.denied}
                    </dd>
                  </div>
                </div>
              </div>

              {/* Average Processing Time Card */}
              <div className="mt-5 bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                <div className="px-4 py-5 sm:p-6">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Average Processing Time
                  </dt>
                  <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
                    {stats.averageProcessingTime}s
                  </dd>
                </div>
              </div>
              
              {/* Placeholder for recent activity */}
              <div className="mt-5 bg-white dark:bg-gray-800 shadow rounded-lg">
                <div className="px-4 py-5 sm:p-6">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">Recent Activity</h3>
                  <div className="mt-4 text-gray-500 dark:text-gray-400">
                    <p>Recent activity will be displayed here. This will include:</p>
                    <ul className="list-disc pl-5 mt-2 space-y-1">
                      <li>Recently processed messages</li>
                      <li>New messages requiring approval</li>
                      <li>System notifications</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
} 