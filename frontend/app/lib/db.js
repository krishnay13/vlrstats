// frontend/app/lib/db.js

import { createRequire } from 'module';
import path from 'path';
import { fileURLToPath } from 'url';

// Create __dirname equivalent in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Create require function
const require = createRequire(import.meta.url);
const Database = require('better-sqlite3');

// Define the path to your SQLite database using path.join for portability
const dbPath = path.join(__dirname, '..', '..', 'valorant_esports.db'); // Adjust based on your project structure

// Initialize the database connection without verbose logging
const db = new Database(dbPath); // Removed the { verbose: false } option

export default db;
