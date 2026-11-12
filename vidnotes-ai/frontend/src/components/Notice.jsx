import { AlertCircle, Info } from 'lucide-react';

export default function Notice({ variant = 'info', title, children, actions }) {
  const Icon = variant === 'error' ? AlertCircle : Info;
  return (
    <div className={`notice notice-${variant}`} role={variant === 'error' ? 'alert' : 'status'}>
      <Icon size={18} />
      <div>
        {title && <p className="notice-title">{title}</p>}
        {children && <div>{children}</div>}
        {actions && <div className="notice-actions">{actions}</div>}
      </div>
    </div>
  );
}
