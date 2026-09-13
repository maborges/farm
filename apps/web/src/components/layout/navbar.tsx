'use client';

import * as React from 'react';
import {
  Bell,
  Search,
  Settings,
  User,
  LogOut,
  HelpCircle,
  Moon,
  Sun,
  Palette,
  Building2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/use-auth-store';

export function Navbar() {
  const { user } = useAuthStore();
  const [isDarkMode, setIsDarkMode] = React.useState(true);

  return (
    <header className="glass-chrome flex items-center justify-between h-16 px-6 sticky top-0 z-30">
      {/* Search area */}
      <div className="flex items-center flex-1 max-w-md">
        <div className="relative w-full group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-primary group-focus-within:text-primary/80 transition-colors" />
          <Input 
            placeholder="Search dashboard..." 
            className="pl-10 h-9 border-border/60 bg-background/45 font-medium text-foreground shadow-sm backdrop-blur-sm focus:border-primary/50 focus:ring-primary/20 transition-all dark:bg-background/20"
          />
        </div>
      </div>

      {/* Action area */}
      <div className="flex items-center gap-3">
        <Button 
          variant="outline" 
          size="sm" 
          className="size-8 p-0 border-border/60 bg-background/45 group relative dark:bg-background/20"
          aria-label="Alternar tema"
          onClick={() => setIsDarkMode(!isDarkMode)}
        >
          {isDarkMode ? (
            <Sun className="size-4 text-primary group-hover:text-amber-500 transition-colors" />
          ) : (
            <Moon className="size-4 text-primary transition-colors" />
          )}
        </Button>

        <Button 
          variant="outline" 
          size="sm" 
          className="size-8 p-0 border-border/60 bg-background/45 group relative dark:bg-background/20"
          aria-label="Notificações"
        >
          <Bell className="size-4 text-primary transition-colors" />
          <span className="absolute top-1 right-1 size-2 rounded-full bg-primary border-2 border-background"></span>
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger>
            <Button 
              variant="outline" 
              size="sm" 
              className="flex items-center gap-2 h-9 px-2 border-border/60 bg-background/45 hover:bg-background/70 transition-all font-semibold dark:bg-background/20 dark:hover:bg-background/35"
            >
              <div className="size-6 rounded-full bg-primary flex items-center justify-center text-[10px] text-primary-foreground font-bold tracking-tighter shadow-sm ring-1 ring-primary/20">
                {user?.role === 'super-admin' ? 'SA' : 'AD'}
              </div>
              <span className="text-xs text-foreground">
                {user?.role === 'super-admin' ? 'Super Admin' : 'Admin'}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="glass-surface w-56 mt-2">
            <DropdownMenuLabel className="flex flex-col gap-1 px-3 py-2">
              <span className="text-sm font-bold text-foreground leading-none">Rodolfo Farmer</span>
              <span className="text-[10px] text-muted-foreground font-medium">rodolfo@agromaster.com</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="border-border" />
            
            <DropdownMenuItem className="gap-2 px-3 py-2 cursor-pointer focus:bg-muted focus:text-foreground">
              <User className="size-4 text-primary" />
              <span className="text-sm">My Profile</span>
            </DropdownMenuItem>
            
            <DropdownMenuItem className="gap-2 px-3 py-2 cursor-pointer focus:bg-muted focus:text-foreground">
              <HelpCircle className="size-4 text-primary" />
              <span className="text-sm">Help & FAQ</span>
            </DropdownMenuItem>
            
            <DropdownMenuLabel className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Appearance</DropdownMenuLabel>
            <DropdownMenuItem onClick={() => setIsDarkMode(false)} className="px-3 py-2 flex items-center gap-2 cursor-pointer focus:bg-muted">
              <Sun className="size-4 text-primary" /> <span className="text-sm">Light Mode</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setIsDarkMode(true)} className="px-3 py-2 flex items-center gap-2 cursor-pointer focus:bg-muted">
              <Moon className="size-4 text-primary" /> <span className="text-sm">Dark Mode</span>
            </DropdownMenuItem>
            <DropdownMenuItem className="px-3 py-2 flex items-center gap-2 cursor-pointer focus:bg-muted">
              <Building2 className="size-4 text-primary" /> <span className="text-sm">System</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator className="border-border" />
            <DropdownMenuItem className="gap-2 px-3 py-2 cursor-pointer focus:bg-destructive/10 focus:text-destructive text-destructive">
              <LogOut className="size-4" />
              <span className="text-sm font-semibold">Sign Out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
