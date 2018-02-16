"""License {{{
GDB Extensions for xv6 Debugging
Copyright © 2018 Robert Underwood
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY Robert Underwood ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL Robert Underwood BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation
are those of the authors and should not be interpreted as representing
official policies, either expressed or implied, of Robert Underwood.
}}}"""
#imports {{{
import gdb
import traceback
#}}}

#Constants {{{
FLAGS = { 
    "PTE_P": 0x001,
    "PTE_W": 0x002,
    "PTE_U": 0x004,
    "PTE_PWT": 0x008,
    "PTE_PCD": 0x010,
    "PTE_A"  : 0x020,
    "PTE_D"  : 0x040,
    "PTE_PS" : 0x080,
    "PTE_MBZ": 0x180,
    }
PDX_SHIFT = 22
PTX_SHIFT = 12
PAGE_SIZE = 4096
KERNBASE = 0x80000000 
# }}}
# Printers {{{ 
# Process Table {{{
class PtablePrinter:
    """pretty printer for the ptable"""

    def __init__(self, ptable):
        self.ptable = ptable

    def to_string(self):
        desc = []
        procs = self.ptable['proc']
        for i in range(64):
            proc = procs[i]
            if str(proc['state']) != "UNUSED":
                desc.append('{name} ({pid}): {state}'.format(
                        name= proc['name'],
                        pid= proc['pid'],
                        state= proc['state']
                    ))
        return '\n'.join(desc) + '\n'

#}}}
# Page Table{{{
# Utilities {{{
class PTEUtil:
    """base class that provides static methods for page table manipulation"""
    def __init__(self, pgdir):
        self.pgdir = pgdir

    def walkpgdir(self, vaddr):
        pde_t = gdb.lookup_type('uint').pointer()
        pde = self.pgdir[self.pdx(vaddr)].address
        pgtab = self.p2v(self.pte_addr(pde.dereference())).cast(pde_t)
        return pgtab[self.ptx(vaddr)].address


    @staticmethod
    def pdx(pte):
        return (pte >> PDX_SHIFT) & 0x3FF

    @staticmethod
    def ptx(pte):
        return (pte >> PTX_SHIFT) & 0x3FF

    @staticmethod
    def p2v(addr):
        return addr+KERNBASE

    @staticmethod
    def pte_addr(pte):
        return pte & ~0xFFF

    @staticmethod
    def flags(pte):
        return set(key for key,value in FLAGS.items() if pte&value != 0)

    @staticmethod
    def is_shared(paddr):
        return "Not Implemented"





class PTEPrinter(PTEUtil):
    """pretty printer for page table entries"""

    def __init__(self, pgdir, sz):
        super().__init__(pgdir)
        self.sz = sz

    def to_string(self):
        desc = []
        for addr in range(0,self.sz,PAGE_SIZE):
            pte = self.walkpgdir(addr)
            flags = self.flags(pte.dereference())
            pa = self.pte_addr(pte.dereference())
            desc.append("addr {addr:08x}, paddr {paddr:08x}, flags {flags}".format(
                addr=addr, paddr=int(pa), flags=flags))
        return "\n".join(desc) + "\n"

class PDEPrinter(PTEUtil):
    """pretty printer for page table directory entries"""
    def __init__(self, pgdir):
        super().__init__(pgdir)

    def to_string(self):
        desc = []
        for i in range(0,1024):
            pde = self.pgdir[i]
            flags = self.flags(pde)
            if 'PTE_P' in flags:
                pa = int(self.pte_addr(pde))
                desc.append("index={index} paddr={addr:08x}, shared={shared}".format(
                    index=i,
                    addr=pa,
                    shared=self.is_shared(pa)
                    ))

        return '\n'.join(desc) + '\n'
#}}}
#}}}
# Commands {{{
class PTEPrinterCommand(gdb.Command):
    """command to summarize the page table
    usage:
    print_pte
    print_pte myproc
    print_pte pgdir sz
    """
    def __init__(self):
        super().__init__('print_pte', gdb.COMMAND_USER, gdb.COMPLETE_SYMBOL)
    def invoke(self, args, from_tty):
        try:
            argv = gdb.string_to_argv(args)
            if len(argv) == 0:
                symbol = 'curproc'
            elif len(argv) == 1:
                symbol = argv[0]
                proc = gdb.selected_frame().read_var(symbol)
                pgdir = proc['pgdir']
                sz    = proc['sz']
            elif len(argv) == 2:
                pgdir = gdb.selected_frame().read_var(argv[0])
                try:
                    sz = int(argv[1],16)
                except ValueError:
                    try:
                        sz = int(argv[1])
                    except ValueError:
                        sz = gdb.selected_frame().read_var(argv[1])
            printer = PTEPrinter(pgdir, sz)
            gdb.write(printer.to_string())
        except Exception as e:
            gdb.write(traceback.format_exc())

class PDEPrinterCommand(gdb.Command):
    """command to sumerize the page directory entries"""

    def __init__(self):
        super().__init__('print_pde', gdb.COMMAND_USER, gdb.COMPLETE_SYMBOL)

    def invoke(self, args, from_tty):
        try:
            argv = gdb.string_to_argv(args)
            if len(argv) < 1:
                symbol = 'pgdir'
            else:
                symbol = argv[0]
            pgdir = gdb.selected_frame().read_var(symbol)
            printer = PDEPrinter(pgdir)
            gdb.write(printer.to_string())
        except Exception as e:
            gdb.write(traceback.format_exc())


class PrintPtableCommand(gdb.Command):
    """write the xv6 ptable in a concise form skipping unused processes
    
    usage: print_ptable
    """
    def __init__(self):
        super().__init__('print_ptable', gdb.COMMAND_USER)

    def invoke(self, args, from_tty):
        ptable = gdb.selected_frame().read_var("ptable")
        printer = PtablePrinter(ptable)
        gdb.write(printer.to_string())
#}}}
#Register Commands with gdb {{{
PTEPrinterCommand()
PDEPrinterCommand()
PrintPtableCommand()
#}}}
# vim: foldmethod=marker:
