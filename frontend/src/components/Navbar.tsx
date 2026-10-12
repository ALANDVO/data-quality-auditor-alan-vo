import React from 'react';
import { UserProfile } from '../api/client';

interface NavbarProps {
  user: UserProfile | null;
  onRoleSwitch: (role: string) => void;
  activeRole: string;
}

export const Navbar: React.FC<NavbarProps> = ({ user, onRoleSwitch, activeRole }) => {
  return (
    <header className="navbar">
      <div className="navbar-brand">
        <div className="brand-logo">DQ</div>
        <div>
          <h1 className="brand-title">Data Quality Auditor</h1>
          <p className="brand-subtitle">Alan Vo | AI & Machine Learning</p>
        </div>
      </div>

      <div className="navbar-controls">
        <div className="demo-role-selector">
          <span className="role-label">Demo Role:</span>
          {(['admin', 'analyst', 'viewer'] as const).map((r) => (
            <button
              key={r}
              className={`role-btn ${activeRole === r ? 'active' : ''}`}
              onClick={() => onRoleSwitch(r)}
            >
              {r.toUpperCase()}
            </button>
          ))}
        </div>

        {user && (
          <div className="user-badge">
            <span className="user-name">{user.username}</span>
            <span className="user-roles">{user.roles.join(', ')}</span>
          </div>
        )}
      </div>
    </header>
  );
};
