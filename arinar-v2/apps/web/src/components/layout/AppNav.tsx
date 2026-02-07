'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import styles from './AppNav.module.css';

export default function AppNav() {
  const pathname = usePathname();

  const isActive = (path: string) => {
    if (path === '/') return pathname === '/';
    return pathname.startsWith(path);
  };

  return (
    <nav className={styles.nav}>
      <div className={styles.container}>
        <Link href="/" className={styles.logo}>
          <span className={styles.wordmark}>Arinar</span>
          <span className={styles.tagline}>Decision Room</span>
        </Link>

        <div className={styles.links}>
          <Link
            href="/"
            className={`${styles.link} ${isActive('/') && !pathname.includes('/setup') && !pathname.includes('/room') && !pathname.includes('/operator') && !pathname.includes('/settings') ? styles.active : ''}`}
          >
            Home
          </Link>
          <Link
            href="/setup"
            className={`${styles.link} ${isActive('/setup') ? styles.active : ''}`}
          >
            Setup
          </Link>
          <Link
            href="/room"
            className={`${styles.link} ${isActive('/room') ? styles.active : ''}`}
          >
            Room
          </Link>
          <Link
            href="/operator"
            className={`${styles.link} ${isActive('/operator') ? styles.active : ''}`}
          >
            Operator
          </Link>
          <Link
            href="/settings"
            className={`${styles.link} ${isActive('/settings') ? styles.active : ''}`}
          >
            Settings
          </Link>
        </div>

        <div className={styles.status}>
          <span className={styles.badge}>Demo Mode</span>
        </div>
      </div>
    </nav>
  );
}
