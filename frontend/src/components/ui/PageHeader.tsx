import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  children?: ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  subtitle,
  children,
  className = '',
}: PageHeaderProps) {
  return (
    <header className={`bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white truncate">
              {title}
            </h1>
            {subtitle && (
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {subtitle}
              </p>
            )}
          </div>
          
          {children && (
            <div className="flex items-center space-x-4">
              {children}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}