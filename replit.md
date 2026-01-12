# MRX System - Gestão de Compras de Sucata Eletrônica

### Overview
The MRX System is a comprehensive platform designed to manage electronic scrap purchases. Its primary purpose is to streamline procurement, enhance pricing control, and improve supplier management within the electronic scrap industry. Key capabilities include a star-based pricing system, a price authorization workflow for negotiations, and geolocation tracking for suppliers. The system also integrates an AI-powered PCB scanner for material classification, an AI chatbot for system interaction, and a financial achievement planning tool for administrators.

### User Preferences
I want iterative development.
I prefer detailed explanations.
Ask before making major changes.
Do not make changes to the folder `Z`.
Do not make changes to the file `Y`.

### System Architecture

#### UI/UX Decisions
The frontend uses Vanilla JavaScript and Tailwind CSS, providing a modern, responsive interface with PWA capabilities via Service Workers. The design focuses on clarity and efficiency for managing materials, prices, and authorizations.

#### Technical Implementations
The system is built on a Flask backend (Python 3.12) with SQLAlchemy for ORM and PostgreSQL (Neon-backed) as the database. Real-time notifications are managed via Socket.IO, and JWT handles authentication.

#### Feature Specifications
-   **Material Management**: Supports over 50 types of electronic scrap with detailed classification.
-   **Star-Based Pricing**: Utilizes three fixed price tables (1★, 2★, 3★) linked to supplier quality, with specific prices per material.
-   **Price Authorization Workflow**: Triggers an authorization request for negotiated prices exceeding standard star-level rates, including status tracking and percentage difference calculation.
-   **Supplier Geolocalization**: Stores supplier location data, with new suppliers defaulting to 1★.
-   **Supplier Tax ID Flexibility**: Supports both CPF (individual) and CNPJ (business) tax IDs with validation.
-   **Freight Modality**: Includes FOB or CIF freight options in purchase requests.
-   **Excel Import/Export**: Functionality for bulk import and export of materials and price tables.
-   **Purchase Wizard**: A multi-step wizard for new purchases, integrating supplier selection, collection/delivery details, item scanning, value input, and authorization requests.
-   **WMS (Warehouse Management System)**: Manages inventory lots with features like lot details viewing, direct search, null-safe user validations, and real-time status tracking.
-   **PCB Scanner with OpenCV + Perplexity**: Implements intelligent electronic board scanning using OpenCV for local image analysis (component detection, density calculation) and Perplexity AI for generating user-friendly explanations. Classification (LOW/MEDIUM/HIGH grade) is based on component count and density analysis. Price suggestions are calculated based on grade and weight. The scanner and chatbot widgets are restricted to admin users only.
-   **AI Chatbot with System Actions**: An enhanced AI assistant (floating widget) capable of executing system actions via natural language, such as creating suppliers, sending notifications, listing data, and generating summaries, with comprehensive database context provided by Perplexity AI.
-   **Achievement Planning**: An admin-only feature for tracking financial goals across various categories, with CRUD operations, progress charts, and AI-powered recommendations.
-   **Supplier Price Table Management**: Allows suppliers to submit and correct price tables, with an admin review interface for side-by-side comparison, inline editing, and bulk approval/rejection.
-   **HR Module (RH)**: A comprehensive human resources module accessible at `/rh-admin.html` with the following features:
    -   **User Management**: Full CRUD for employees with photo upload, profile assignment, contact information (phone, CPF), and status management.
    -   **Commission System**: Percentage-based commission tracking tied to purchase solicitations (solicitações), with assignment of commission percentages per user.
    -   **Commission Reports**: Detailed reporting with filtering by date range and user, showing total value of solicitations and calculated commissions.
    -   **Export Functionality**: CSV and Excel export for commission reports using pandas/openpyxl.
    -   **Audit Logging**: Complete audit trail for all HR operations using the existing AuditoriaLog system, tracking before/after changes.
    -   **User Photo Uploads**: Photos stored in the database as binary data (`foto_data` column) for Railway compatibility, with validation for image types and size limits. The system uses BYTEA columns to persist photos across container restarts.
-   **Supplier Visits Module (Visitas)**: A complete visit tracking system integrated into the suppliers page (`/fornecedores.html`) with the following features:
    -   **Visit Registration**: Create visits with supplier name, contact info (name, email, phone), observations, and automatic GPS geolocation capture.
    -   **Tab-Based Interface**: Toggle between "Fornecedores" and "Visitas" tabs within the same page.
    -   **Status Workflow**: Three states - pendente (pending), nao_fechado (not closed), negociacao_fechada (deal closed).
    -   **Visit Cards**: Visual display of all visits with status badges, contact info preview, and action buttons.
    -   **Detail Modal**: Full visit details including Google Maps link for GPS coordinates.
    -   **Continuity Flow**: When marking a visit as "negociação fechada", the system pre-fills the supplier registration form with the visit's contact data.

#### System Design Choices
-   **Database Models**: Key models include `MaterialBase`, `TabelaPreco`, `TabelaPrecoItem`, `SolicitacaoAutorizacaoPreco`, `Fornecedor` (extended with `tipo_documento`, `cpf`, `cnpj`), `Solicitacao` (with `modalidade_frete`), `ScannerConfig`, `ScannerAnalysis`, `Conquista`, `AporteConquista`, `Usuario` (extended with `foto_path`, `percentual_comissao`, `telefone`, `cpf`, `data_atualizacao` for HR module), and `VisitaFornecedor` (with GPS coordinates, contact info, status workflow, and foreign keys to Usuario and Fornecedor).
-   **API Endpoints**: Structured RESTful APIs for managing materials, price tables, authorizations, suppliers, purchases, and the AI scanner, including CRUD, bulk updates, and Excel integrations. Specific endpoints for CEP lookup and AI assistant actions are also present.
-   **Security**: Employs JWT for authentication, role-based authorization (`@admin_required`), robust input validation (e.g., prices, weights, CPF/CNPJ format/uniqueness), and database integrity checks.
-   **Seed Data**: An idempotent seed script initializes essential system data.
-   **Database Migrations**: Handles schema changes including additions for CPF/CNPJ support and freight modality tracking.

### External Dependencies

#### Backend
-   Flask
-   Flask-SQLAlchemy
-   Flask-JWT-Extended
-   Flask-SocketIO
-   psycopg2-binary
-   pandas
-   openpyxl
-   OpenCV (opencv-python-headless)
-   NumPy
-   Perplexity AI API (for text explanations)

#### Frontend
-   Tailwind CSS
-   Chart.js
-   Socket.IO Client