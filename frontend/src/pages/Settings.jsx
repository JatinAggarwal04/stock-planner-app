import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { User, Bell, Shield, Trash2 } from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'

export default function Settings() {
  const { user } = useAuth()
  
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-dark-bg py-8">
      <div className="max-w-4xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-8">
          Settings
        </h1>

        <div className="space-y-6">
          {/* Profile Section */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <User className="w-6 h-6 text-primary-600" />
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                Profile
              </h2>
            </div>

            <div className="space-y-4">
              <Input
                label="Email"
                type="email"
                value={user?.email}
                disabled
              />
              
              <p className="text-sm text-slate-500">
                Contact support to change your email address
              </p>
            </div>
          </Card>

          {/* Notifications */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Bell className="w-6 h-6 text-primary-600" />
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                Notifications
              </h2>
            </div>

            <div className="space-y-4">
              <label className="flex items-center justify-between">
                <span className="text-slate-700 dark:text-slate-300">Price alerts</span>
                <input type="checkbox" className="w-5 h-5" />
              </label>
              
              <label className="flex items-center justify-between">
                <span className="text-slate-700 dark:text-slate-300">News updates</span>
                <input type="checkbox" className="w-5 h-5" />
              </label>
            </div>
          </Card>

          {/* Danger Zone */}
          <Card className="p-6 border-danger-200 dark:border-danger-800">
            <div className="flex items-center gap-3 mb-6">
              <Trash2 className="w-6 h-6 text-danger-600" />
              <h2 className="text-xl font-bold text-danger-600 dark:text-danger-400">
                Danger Zone
              </h2>
            </div>

            <Button variant="danger">
              Delete Account
            </Button>
          </Card>
        </div>
      </div>
    </div>
  )
}