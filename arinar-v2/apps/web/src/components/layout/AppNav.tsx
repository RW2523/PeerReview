'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import UserMenu from './UserMenu';
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

        <div className={styles.navRight}>
          <div className={styles.links}>
            <Link
              href="/"
              className={`${styles.link} ${isActive('/') && !pathname.includes('/room') && !pathname.includes('/settings') && !pathname.includes('/history') ? styles.active : ''}`}
            >
              Create Debate
            </Link>
            <Link
              href="/room"
              className={`${styles.link} ${isActive('/room') ? styles.active : ''}`}
            >
              Room
            </Link>
          </div>

          <UserMenu />
        </div>
      </div>
    </nav>
  );
}
