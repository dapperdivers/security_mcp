#!/bin/bash
# Bearer MCP Server - Local SBOM Generation Script
# This script generates Software Bill of Materials for local development and testing

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SBOM_OUTPUT_DIR="${PROJECT_ROOT}/sbom-output"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Python SBOM tools
install_sbom_tools() {
    print_info "Installing SBOM generation tools..."
    
    pip install --upgrade pip setuptools wheel
    pip install 'cyclonedx-python-lib>=7.0.0,<10.0.0' 'pip-audit>=2.9.0' cyclonedx-py cyclonedx-bom>=4.0.0
    
    print_success "SBOM tools installed"
}

# Function to generate Python SBOMs
generate_python_sbom() {
    print_info "Generating Python SBOM..."
    
    cd "$PROJECT_ROOT"
    mkdir -p "$SBOM_OUTPUT_DIR"
    
    # Generate SBOM from environment
    print_info "Generating environment SBOM..."
    cyclonedx-py environment \
        --of JSON \
        --output-file "$SBOM_OUTPUT_DIR/sbom-python-env-$TIMESTAMP.json"
    
    # Generate SBOM from requirements
    if [ -f "requirements.txt" ]; then
        print_info "Generating requirements SBOM..."
        cyclonedx-py requirements requirements.txt \
            --of JSON \
            --output-file "$SBOM_OUTPUT_DIR/sbom-python-requirements-$TIMESTAMP.json"
    fi
    
    # Generate vulnerability SBOM with pip-audit
    print_info "Generating vulnerability SBOM with pip-audit..."
    pip-audit \
        --format=cyclonedx-json \
        --output="$SBOM_OUTPUT_DIR/sbom-vulnerabilities-$TIMESTAMP.json" || {
        print_warning "pip-audit completed with warnings (vulnerabilities may exist)"
    }
    
    print_success "Python SBOMs generated"
}

# Function to generate container SBOM
generate_container_sbom() {
    local image_name="$1"
    print_info "Generating container SBOM for image: $image_name"
    
    if command_exists syft; then
        syft "$image_name" -o spdx-json="$SBOM_OUTPUT_DIR/sbom-container-syft-$TIMESTAMP.spdx.json"
        print_success "Container SBOM generated with Syft"
    else
        print_warning "Syft not found. Install with: curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin"
    fi
    
    if command_exists trivy; then
        trivy image --format spdx-json --output "$SBOM_OUTPUT_DIR/sbom-container-trivy-$TIMESTAMP.spdx.json" "$image_name"
        print_success "Container SBOM generated with Trivy"
    else
        print_warning "Trivy not found. Install from: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
    fi
}

# Function to validate SBOMs
validate_sboms() {
    print_info "Validating generated SBOMs..."
    
    local validation_failed=0
    
    for sbom_file in "$SBOM_OUTPUT_DIR"/*.json; do
        if [ -f "$sbom_file" ]; then
            if jq -e '.bomFormat == "CycloneDX"' "$sbom_file" >/dev/null 2>&1; then
                local components=$(jq '.components | length' "$sbom_file" 2>/dev/null || echo 0)
                print_success "$(basename "$sbom_file"): Valid CycloneDX format with $components components"
            else
                print_error "$(basename "$sbom_file"): Invalid CycloneDX format"
                validation_failed=1
            fi
        fi
    done
    
    for sbom_file in "$SBOM_OUTPUT_DIR"/*.spdx.json; do
        if [ -f "$sbom_file" ]; then
            if jq -e '.spdxVersion' "$sbom_file" >/dev/null 2>&1; then
                local packages=$(jq '.packages | length' "$sbom_file" 2>/dev/null || echo 0)
                print_success "$(basename "$sbom_file"): Valid SPDX format with $packages packages"
            else
                print_error "$(basename "$sbom_file"): Invalid SPDX format"
                validation_failed=1
            fi
        fi
    done
    
    if [ $validation_failed -eq 0 ]; then
        print_success "All SBOMs validated successfully"
    else
        print_error "SBOM validation failed"
        return 1
    fi
}

# Function to generate summary report
generate_summary() {
    print_info "Generating SBOM summary report..."
    
    local summary_file="$SBOM_OUTPUT_DIR/sbom-summary-$TIMESTAMP.json"
    
    cat > "$summary_file" << EOF
{
  "generated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "generator": "Bearer MCP Server SBOM Generator",
  "version": "1.0.0",
  "project": {
    "name": "bearer-mcp-server",
    "path": "$PROJECT_ROOT"
  },
  "sboms": {
    "python": [
$(ls "$SBOM_OUTPUT_DIR"/sbom-python-*.json 2>/dev/null | sed 's/.*/"&"/' | paste -sd ',' || echo '""')
    ],
    "container": [
$(ls "$SBOM_OUTPUT_DIR"/sbom-container-*.spdx.json 2>/dev/null | sed 's/.*/"&"/' | paste -sd ',' || echo '""')
    ],
    "vulnerabilities": [
$(ls "$SBOM_OUTPUT_DIR"/sbom-vulnerabilities-*.json 2>/dev/null | sed 's/.*/"&"/' | paste -sd ',' || echo '""')
    ]
  },
  "hashes": {
$(for file in "$SBOM_OUTPUT_DIR"/sbom-*.json "$SBOM_OUTPUT_DIR"/sbom-*.spdx.json; do
    if [ -f "$file" ]; then
        hash=$(sha256sum "$file" | cut -d' ' -f1)
        echo "    \"$(basename "$file")\": \"$hash\","
    fi
done | sed '$ s/,$//')
  }
}
EOF
    
    print_success "Summary report generated: $summary_file"
}

# Function to display help
show_help() {
    cat << EOF
Bearer MCP Server - SBOM Generation Script

Usage: $0 [OPTIONS] [COMMANDS]

Commands:
  python                Generate Python SBOMs
  container IMAGE       Generate container SBOM for specified image
  validate             Validate all generated SBOMs
  summary              Generate summary report
  all                  Run all SBOM generation steps (python + validate + summary)
  clean               Remove old SBOM files

Options:
  -h, --help          Show this help message
  -v, --verbose       Enable verbose output
  --install-tools     Install required SBOM generation tools
  --output-dir DIR    Specify output directory (default: ./sbom-output)

Examples:
  $0 python                                    # Generate Python SBOMs
  $0 container bearer-mcp:latest               # Generate container SBOM
  $0 all                                       # Generate all SBOMs
  $0 --install-tools python                   # Install tools and generate Python SBOMs
  $0 --output-dir /tmp/sboms validate         # Validate SBOMs in custom directory

EOF
}

# Function to clean old SBOM files
clean_sboms() {
    print_info "Cleaning old SBOM files..."
    
    if [ -d "$SBOM_OUTPUT_DIR" ]; then
        find "$SBOM_OUTPUT_DIR" -name "sbom-*" -type f -mtime +7 -delete 2>/dev/null || true
        print_success "Cleaned SBOM files older than 7 days"
    else
        print_info "No SBOM output directory found"
    fi
}

# Main execution
main() {
    local install_tools=false
    local verbose=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                set -x
                shift
                ;;
            --install-tools)
                install_tools=true
                shift
                ;;
            --output-dir)
                SBOM_OUTPUT_DIR="$2"
                shift 2
                ;;
            python|container|validate|summary|all|clean)
                break
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Check if we have any commands
    if [[ $# -eq 0 ]]; then
        print_error "No command specified"
        show_help
        exit 1
    fi
    
    # Install tools if requested
    if [ "$install_tools" = true ]; then
        install_sbom_tools
    fi
    
    # Check for required tools
    if ! command_exists jq; then
        print_error "jq is required but not installed"
        exit 1
    fi
    
    # Execute commands
    while [[ $# -gt 0 ]]; do
        case $1 in
            python)
                generate_python_sbom
                shift
                ;;
            container)
                if [[ $# -lt 2 ]]; then
                    print_error "Container command requires image name"
                    exit 1
                fi
                generate_container_sbom "$2"
                shift 2
                ;;
            validate)
                validate_sboms
                shift
                ;;
            summary)
                generate_summary
                shift
                ;;
            all)
                generate_python_sbom
                validate_sboms
                generate_summary
                shift
                ;;
            clean)
                clean_sboms
                shift
                ;;
            *)
                print_error "Unknown command: $1"
                exit 1
                ;;
        esac
    done
    
    print_success "SBOM generation completed. Output directory: $SBOM_OUTPUT_DIR"
}

# Check if script is being sourced or executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi