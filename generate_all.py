#!/usr/bin/env python3
"""
Dynamically load and run all ChartController implementations.

This script discovers all classes that extend ChartController in the
tpsplots.controllers package and executes their generate_charts() method.
"""

import importlib
import inspect
import pkgutil
import logging
import sys
from pathlib import Path
import time
import os
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tpsplots.controllers.chart_controller import ChartController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)


def count_files_modified_after(directory, start_time, extensions=None):
    """
    Count files in directory modified after start_time.
    
    Args:
        directory: Path to scan
        start_time: Unix timestamp
        extensions: List of extensions to count (e.g., ['.png', '.svg'])
        
    Returns:
        tuple: (total_count, dict of counts by extension)
    """
    if not directory.exists():
        return 0, {}
        
    total_count = 0
    count_by_ext = {}
    
    # Default extensions if not provided
    if extensions is None:
        extensions = ['.svg', '.png', '.pptx', '.csv']
    
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            # Check if file was modified after start time
            mtime = file_path.stat().st_mtime
            if mtime >= start_time:
                # Check if it's a file type we're interested in
                ext = file_path.suffix.lower()
                if not extensions or ext in extensions:
                    total_count += 1
                    count_by_ext[ext] = count_by_ext.get(ext, 0) + 1
                    
    return total_count, count_by_ext


def discover_controller_classes():
    """
    Discover all classes that inherit from ChartController in the controllers package.
    
    Returns:
        dict: A dictionary mapping class names to class objects
    """
    controllers = {}
    
    # Import the controllers package
    import tpsplots.controllers as controllers_package
    
    # Get the package path
    package_path = Path(controllers_package.__file__).parent
    
    # Iterate through all modules in the controllers package
    for importer, module_name, ispkg in pkgutil.iter_modules([str(package_path)]):
        if ispkg:
            continue  # Skip sub-packages
            
        # Skip the base chart_controller module
        if module_name == 'chart_controller':
            continue
            
        try:
            # Import the module dynamically
            full_module_name = f'tpsplots.controllers.{module_name}'
            logger.debug(f"Importing module: {full_module_name}")
            module = importlib.import_module(full_module_name)
            
            # Inspect the module for classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if the class inherits from ChartController
                if (issubclass(obj, ChartController) and 
                    obj != ChartController and 
                    obj.__module__ == full_module_name):
                    logger.debug(f"Found controller class: {name}")
                    controllers[name] = obj
                    
        except Exception as e:
            logger.error(f"Error importing module {module_name}: {e}")
            
    return controllers


def run_all_controllers():
    """
    Discover and run all ChartController implementations.
    """
    logger.info("Starting chart generation...")
    
    # Record start time
    start_time = time.time()
    
    # Get the charts output directory
    charts_dir = Path("charts")
    
    # Discover all controller classes
    controller_classes = discover_controller_classes()
    
    if not controller_classes:
        logger.warning("No controller classes found!")
        return
    
    logger.info(f"Found {len(controller_classes)} chart generators: {', '.join(controller_classes.keys())}")
    
    # Track successes and failures
    successful = []
    failed = []
    controller_file_counts = {}
    
    # Instantiate and run each controller
    for class_name, controller_class in controller_classes.items():
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {class_name}")
            logger.info(f"{'='*60}")
            
            # Record time before this controller
            controller_start = time.time()
            
            # Instantiate the controller
            controller = controller_class()
            
            # Call the generate_charts method
            controller.generate_charts()
            
            # Count files created by this controller
            controller_files, _ = count_files_modified_after(
                controller.outdir if hasattr(controller, 'outdir') else charts_dir,
                controller_start
            )
            controller_file_counts[class_name] = controller_files
            
            successful.append(class_name)
            logger.info(f"Successfully completed charts for {class_name} ({controller_files} files)")
            
        except Exception as e:
            failed.append((class_name, str(e)))
            logger.error(f"Error running {class_name}: {e}", exc_info=True)
    
    # Count total files created/modified
    total_files, files_by_type = count_files_modified_after(charts_dir, start_time)
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Execution time: {time.time() - start_time:.1f} seconds")
    logger.info(f"Total files created/modified: {total_files}")
    
    # Show file type breakdown
    if files_by_type:
        logger.info("\nFiles by type:")
        for ext, count in sorted(files_by_type.items()):
            logger.info(f"  {ext}: {count}")
    
    # Show files per controller
    if controller_file_counts:
        logger.info("\nFiles per controller:")
        for controller, count in sorted(controller_file_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {controller}: {count} files")
    
    if successful:
        logger.info(f"\nSuccessful controllers: {len(successful)}")
        logger.info(f"Controllers: {', '.join(successful)}")
    
    if failed:
        logger.error(f"\nFailed controllers: {len(failed)}")
        for class_name, error in failed:
            logger.error(f"  - {class_name}: {error}")


if __name__ == "__main__":
    run_all_controllers()