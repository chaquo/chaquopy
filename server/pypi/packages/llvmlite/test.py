import unittest


class TestLlvmlite(unittest.TestCase):

    # Based on examples from https://llvmlite.readthedocs.io/en/latest/user-guide/index.html.
    def test_basic(self):
        from llvmlite import ir

        # Create some useful types
        double = ir.DoubleType()
        fnty = ir.FunctionType(double, (double, double))

        # Create an empty module...
        module = ir.Module(name=__file__)
        # and declare a function named "fpadd" inside it
        func = ir.Function(module, fnty, name="fpadd")

        # Now implement the function
        block = func.append_basic_block(name="entry")
        builder = ir.IRBuilder(block)
        a, b = func.args
        result = builder.fadd(a, b, name="res")
        builder.ret(result)
        llvm_ir = str(module)

        from ctypes import CFUNCTYPE, c_double
        import llvmlite.binding as llvm

        # All these initializations are required for code generation!
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()  # yes, even this one

        # Create a target machine representing the host
        target = llvm.Target.from_default_triple()
        target_machine = target.create_target_machine()
        # And an execution engine with an empty backing module
        backing_mod = llvm.parse_assembly("")
        engine = llvm.create_mcjit_compiler(backing_mod, target_machine)

        # Create a LLVM module object from the IR
        mod = llvm.parse_assembly(llvm_ir)
        mod.verify()
        # Now add the module and make sure it is ready for execution
        engine.add_module(mod)
        engine.finalize_object()
        engine.run_static_constructors()

        # Look up the function pointer (a Python int)
        func_ptr = engine.get_function_address("fpadd")

        # Run the function via ctypes
        cfunc = CFUNCTYPE(c_double, c_double, c_double)(func_ptr)
        self.assertEqual(9, cfunc(2, 7))
        self.assertEqual(4.5, cfunc(1.0, 3.5))
