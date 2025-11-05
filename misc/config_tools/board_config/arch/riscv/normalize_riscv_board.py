#!/usr/bin/env python3
# Copyright (C) 2025 Intel Corporation.
#
# SPDX-License-Identifier: BSD-3-Clause
#

"""
RISC-V Board Configuration Normalizer - DTS Text Parser

This script normalizes RISC-V board configuration data from Device Tree Source (DTS)
text to a standardized format compatible with ACRN x86 configuration tools.

Uses direct DTS text parsing - no external dependencies required.

Input: RISC-V board XML with embedded Device Tree information
Output: Normalized XML compatible with ACRN x86 configuration format
"""

import sys
import os
import xml.etree.ElementTree as ET
import re
from collections import defaultdict

# Add common library paths
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'library'))

try:
    import acrn_config_utilities
except ImportError:
    # Fallback if library not available
    class MockUtilities:
        @staticmethod
        def print_yel(msg, warn=True):
            print(f"WARNING: {msg}")
        @staticmethod
        def print_red(msg, err=True):
            print(f"ERROR: {msg}")
    acrn_config_utilities = MockUtilities()


class DeviceTreeParser:
    """Parser for Device Tree Source (DTS) text format - no external dependencies"""
    
    def __init__(self, device_tree_text):
        self.dt_text = device_tree_text
        self.cpus = []
        self.memory_regions = []
        self.pci_devices = []
        self.interrupt_controllers = []
        self.peripherals = []
        self.timebase_frequency = 0
        
    def parse(self):
        """Parse Device Tree text directly - fast and reliable"""
        try:
            acrn_config_utilities.print_yel("Parsing Device Tree Source (DTS) text directly...")
            self._parse_dts_text()
            acrn_config_utilities.print_yel("Successfully parsed Device Tree from text")
        except Exception as e:
            acrn_config_utilities.print_red(f"Error parsing Device Tree: {str(e)}")
            raise
    
    def _parse_dts_text(self):
        """Parse DTS text format directly"""
        # Extract timebase frequency
        timebase_match = re.search(r'timebase-frequency\s*=\s*<(0x[0-9a-fA-F]+)>', self.dt_text)
        if timebase_match:
            self.timebase_frequency = int(timebase_match.group(1), 16)
        
        # Extract CPU information with detailed parsing
        self._extract_cpu_info()
        self._extract_memory_info()
        self._extract_pci_info()
        self._extract_interrupt_controllers()
        self._extract_peripherals()
    
    def _extract_cpu_info(self):
        """Extract CPU information from DTS text"""
        cpu_pattern = r'cpu@(\d+)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(cpu_pattern, self.dt_text, re.DOTALL):
            hart_id = int(match.group(1))
            cpu_content = match.group(2)
            
            # Extract ISA string
            isa_match = re.search(r'riscv,isa\s*=\s*"([^"]+)"', cpu_content)
            isa = isa_match.group(1) if isa_match else 'rv64gc'
            
            # Extract compatible
            compatible_match = re.search(r'compatible\s*=\s*"([^"]+)"', cpu_content)
            compatible = compatible_match.group(1) if compatible_match else 'riscv'
            
            # Extract status
            status_match = re.search(r'status\s*=\s*"([^"]+)"', cpu_content)
            status = status_match.group(1) if status_match else 'okay'
            
            self.cpus.append({
                'hart_id': hart_id,
                'cpu_id': hart_id,
                'apic_id': hart_id,
                'isa': isa,
                'compatible': compatible,
                'status': status
            })
    
    def _extract_memory_info(self):
        """Extract memory information from DTS text"""
        memory_pattern = r'memory@([0-9a-fA-F]+)\s*\{([^}]+)\}'
        for match in re.finditer(memory_pattern, self.dt_text, re.DOTALL):
            base_addr_str = match.group(1)
            memory_content = match.group(2)
            
            # Find reg property
            reg_match = re.search(r'reg\s*=\s*<([^>]+)>', memory_content)
            if reg_match:
                reg_str = reg_match.group(1)
                # Parse hex values
                values = reg_str.strip().split()
                if len(values) >= 4:
                    try:
                        # Handle both hex and decimal values
                        parsed_values = []
                        for val in values:
                            if val.startswith('0x'):
                                parsed_values.append(int(val, 16))
                            else:
                                # Try to parse as hex if it looks like hex
                                try:
                                    parsed_values.append(int(val, 16))
                                except ValueError:
                                    parsed_values.append(int(val))
                        
                        if len(parsed_values) >= 4:
                            base_high, base_low, size_high, size_low = parsed_values[:4]
                            start_addr = (base_high << 32) | base_low
                            size = (size_high << 32) | size_low
                            end_addr = start_addr + size - 1
                            
                            self.memory_regions.append({
                                'start': f"0x{start_addr:016x}",
                                'end': f"0x{end_addr:016x}",
                                'size': size
                            })
                    except ValueError as e:
                        acrn_config_utilities.print_yel(f"Failed to parse memory reg: {e}")
                        continue
    
    def _extract_pci_info(self):
        """Extract PCI information from DTS text"""
        pci_pattern = r'pci@([0-9a-fA-F]+)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(pci_pattern, self.dt_text, re.DOTALL):
            base_addr_str = match.group(1)
            pci_content = match.group(2)
            
            # Find reg property
            reg_match = re.search(r'reg\s*=\s*<([^>]+)>', pci_content)
            if reg_match:
                reg_str = reg_match.group(1)
                values = reg_str.strip().split()
                if len(values) >= 6:  # PCI reg usually has more values
                    try:
                        base_high = int(values[0], 16) if values[0].startswith('0x') else int(values[0], 16)
                        base_low = int(values[1], 16) if values[1].startswith('0x') else int(values[1], 16)
                        size_high = int(values[2], 16) if values[2].startswith('0x') else int(values[2], 16)
                        size_low = int(values[3], 16) if values[3].startswith('0x') else int(values[3], 16)
                        
                        start_addr = (base_high << 32) | base_low
                        size = (size_high << 32) | size_low
                        
                        self.pci_devices.append({
                            'address': '0x0',
                            'description': 'PCI Host bridge: RISC-V Generic PCI Express Root Complex',
                            'vendor': '0x0000',
                            'device': '0x0000',
                            'class': '0x060000',
                            'base_addr': f"0x{start_addr:016x}",
                            'size': size
                        })
                    except ValueError:
                        continue
    
    def _extract_interrupt_controllers(self):
        """Extract PLIC information from DTS text"""
        plic_pattern = r'plic@([0-9a-fA-F]+)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(plic_pattern, self.dt_text, re.DOTALL):
            base_addr_str = match.group(1)
            plic_content = match.group(2)
            
            # Find reg and ndev properties
            reg_match = re.search(r'reg\s*=\s*<([^>]+)>', plic_content)
            ndev_match = re.search(r'riscv,ndev\s*=\s*<(0x[0-9a-fA-F]+)>', plic_content)
            
            if reg_match:
                reg_str = reg_match.group(1)
                values = reg_str.strip().split()
                if len(values) >= 4:
                    try:
                        base_high = int(values[0], 16) if values[0].startswith('0x') else int(values[0], 16)
                        base_low = int(values[1], 16) if values[1].startswith('0x') else int(values[1], 16)
                        reg_base = (base_high << 32) | base_low
                        
                        ndev = int(ndev_match.group(1), 16) if ndev_match else 95
                        
                        self.interrupt_controllers.append({
                            'type': 'plic',
                            'id': '0x0',
                            'address': f"0x{reg_base:08x}",
                            'gsi_base': '0x0',
                            'gsi_number': str(ndev)
                        })
                    except ValueError:
                        continue
    
    def _extract_peripherals(self):
        """Extract peripheral information from DTS text"""
        # Extract serial devices
        serial_pattern = r'serial@([0-9a-fA-F]+)\s*\{([^}]+)\}'
        for match in re.finditer(serial_pattern, self.dt_text, re.DOTALL):
            base_addr_str = match.group(1)
            serial_content = match.group(2)
            
            # Extract properties
            reg_match = re.search(r'reg\s*=\s*<([^>]+)>', serial_content)
            irq_match = re.search(r'interrupts\s*=\s*<(0x[0-9a-fA-F]+)>', serial_content)
            compatible_match = re.search(r'compatible\s*=\s*"([^"]+)"', serial_content)
            
            if reg_match:
                reg_str = reg_match.group(1)
                values = reg_str.strip().split()
                if len(values) >= 4:
                    try:
                        base_high = int(values[0], 16) if values[0].startswith('0x') else int(values[0], 16)
                        base_low = int(values[1], 16) if values[1].startswith('0x') else int(values[1], 16)
                        base_addr = (base_high << 32) | base_low
                        
                        irq = int(irq_match.group(1), 16) if irq_match else 10
                        compatible = compatible_match.group(1) if compatible_match else 'ns16550a'
                        
                        self.peripherals.append({
                            'type': 'serial',
                            'base': f"0x{base_addr:08x}",
                            'irq': str(irq),
                            'clock_frequency': '0x00083800',
                            'compatible': compatible
                        })
                    except ValueError:
                        continue


class RiscvBoardNormalizer:
    """Main normalizer class for RISC-V board configurations"""
    
    def __init__(self, input_file, output_file):
        self.input_file = input_file
        self.output_file = output_file
        self.board_name = "qemu-riscv"
        self.dt_parser = None
        
    def normalize(self):
        """Main normalization process"""
        try:
            # Parse input XML
            tree = ET.parse(self.input_file)
            root = tree.getroot()
            
            # Extract board name
            self.board_name = root.get('board', 'qemu-riscv')
            
            # Extract Device Tree information
            dt_info = root.find('DEVICE_TREE_INFO')
            if dt_info is None:
                acrn_config_utilities.print_red("No DEVICE_TREE_INFO found in input XML")
                return False
                
            # Parse Device Tree using direct text parsing
            self.dt_parser = DeviceTreeParser(dt_info.text)
            self.dt_parser.parse()
            
            # Generate normalized XML
            self._generate_normalized_xml()
            
            acrn_config_utilities.print_yel(f"Successfully normalized {self.input_file} -> {self.output_file}")
            return True
            
        except Exception as e:
            acrn_config_utilities.print_red(f"Error normalizing board configuration: {str(e)}")
            return False
            
    def _generate_normalized_xml(self):
        """Generate clean normalized XML output"""
        root = ET.Element('acrn-config')
        root.set('board', self.board_name)
        root.set('arch', 'riscv')
        
        # Add only essential sections with DTS-derived data
        self._add_cpu_info(root)
        self._add_memory_info(root)
        self._add_interrupt_info(root)
        if self.dt_parser.peripherals:
            self._add_peripheral_info(root)
        
        # Add structured sections
        self._add_processor_topology(root)
        self._add_memory_sections(root)
        self._add_interrupt_controller_sections(root)
        if self.dt_parser.peripherals:
            self._add_device_sections(root)
        
        self._write_xml_file(root)
    
    def _add_cpu_info(self, root):
        """Add CPU information from DTS"""
        if self.dt_parser.cpus:
            cpu_brand = ET.SubElement(root, 'CPU_BRAND')
            cpu_brand.text = self.dt_parser.cpus[0]["isa"]
            
            cpu_processor_info = ET.SubElement(root, 'CPU_PROCESSOR_INFO')
            cpu_ids = [str(cpu['cpu_id']) for cpu in self.dt_parser.cpus]
            cpu_processor_info.text = ', '.join(cpu_ids)
            
            if self.dt_parser.timebase_frequency:
                timebase_info = ET.SubElement(root, 'TIMEBASE_FREQUENCY')
                timebase_info.text = str(self.dt_parser.timebase_frequency)
    
    def _add_memory_info(self, root):
        """Add memory information from DTS"""
        if self.dt_parser.memory_regions:
            total_memory = sum(region['size'] for region in self.dt_parser.memory_regions)
            
            total_mem_info = ET.SubElement(root, 'TOTAL_MEM_INFO')
            total_mem_info.text = str(total_memory // 1024)
            
            for i, region in enumerate(self.dt_parser.memory_regions):
                mem_region = ET.SubElement(root, f'MEMORY_REGION_{i}')
                mem_region.text = f"{region['start']}-{region['end']}"
    
    def _add_interrupt_info(self, root):
        """Add interrupt information from DTS"""
        if self.dt_parser.interrupt_controllers:
            for ic in self.dt_parser.interrupt_controllers:
                if ic['type'] == 'plic':
                    plic_info = ET.SubElement(root, 'PLIC_INFO')
                    plic_info.text = f"base={ic['address']} irqs={ic['gsi_number']}"
    
    def _add_peripheral_info(self, root):
        """Add peripheral information from DTS"""
        for i, peripheral in enumerate(self.dt_parser.peripherals):
            if peripheral['type'] == 'serial':
                serial_info = ET.SubElement(root, f'SERIAL_{i}')
                serial_info.text = f"base={peripheral['base']} irq={peripheral['irq']} compatible={peripheral['compatible']}"
    
    def _add_processor_topology(self, root):
        """Add processor topology from DTS"""
        if self.dt_parser.cpus:
            processors = ET.SubElement(root, 'processors')
            
            for cpu in self.dt_parser.cpus:
                cpu_elem = ET.SubElement(processors, 'cpu')
                cpu_elem.set('id', str(cpu['cpu_id']))
                cpu_elem.set('hart_id', str(cpu['hart_id']))
                cpu_elem.text = cpu['isa']
    
    def _add_memory_sections(self, root):
        """Add memory sections from DTS"""
        if self.dt_parser.memory_regions:
            memory = ET.SubElement(root, 'memory')
            
            for region in self.dt_parser.memory_regions:
                range_elem = ET.SubElement(memory, 'range')
                range_elem.set('start', region['start'])
                range_elem.set('end', region['end'])
                range_elem.set('size', str(region['size']))
    
    def _add_interrupt_controller_sections(self, root):
        """Add interrupt controller sections from DTS"""
        if self.dt_parser.interrupt_controllers:
            interrupt_controllers = ET.SubElement(root, 'interrupt_controllers')
            
            for ic in self.dt_parser.interrupt_controllers:
                if ic['type'] == 'plic':
                    plic = ET.SubElement(interrupt_controllers, 'plic')
                    plic.set('address', ic['address'])
                    plic.set('interrupts', ic['gsi_number'])
    
    def _add_device_sections(self, root):
        """Add device sections from DTS"""
        if self.dt_parser.peripherals:
            devices = ET.SubElement(root, 'devices')
            
            for peripheral in self.dt_parser.peripherals:
                if peripheral['type'] == 'serial':
                    device = ET.SubElement(devices, 'serial')
                    device.set('base', peripheral['base'])
                    device.set('irq', peripheral['irq'])
                    device.set('compatible', peripheral['compatible'])
    
    def _write_xml_file(self, root):
        """Write XML to file with proper formatting"""
        tree = ET.ElementTree(root)
        
        # Format the XML
        self._indent_xml(root)
        
        with open(self.output_file, 'wb') as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            tree.write(f, encoding='utf-8', xml_declaration=False)
    
    def _indent_xml(self, elem, level=0):
        """Add proper indentation to XML elements"""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._indent_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i


def main():
    """Main entry point"""
    if len(sys.argv) != 3:
        print("Usage: normalize_riscv_board.py <input_xml> <output_xml>")
        print("  input_xml:  RISC-V board XML with Device Tree information")
        print("  output_xml: Normalized XML output compatible with ACRN tools")
        return 1
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist")
        return 1
        
    normalizer = RiscvBoardNormalizer(input_file, output_file)
    if normalizer.normalize():
        print(f"Successfully normalized {input_file} to {output_file}")
        return 0
    else:
        print("Normalization failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())