# Generated from /swirlc/grammar/SWIRL.g4 by ANTLR 4.13.1
from antlr4 import *
if "." in __name__:
    from .SWIRLParser import SWIRLParser
else:
    from SWIRLParser import SWIRLParser

# This class defines a complete generic visitor for a parse tree produced by SWIRLParser.

class SWIRLVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SWIRLParser#workflow.
    def visitWorkflow(self, ctx:SWIRLParser.WorkflowContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#location.
    def visitLocation(self, ctx:SWIRLParser.LocationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#TraceParen.
    def visitTraceParen(self, ctx:SWIRLParser.TraceParenContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#TracePred.
    def visitTracePred(self, ctx:SWIRLParser.TracePredContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#TraceOp.
    def visitTraceOp(self, ctx:SWIRLParser.TraceOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#pred.
    def visitPred(self, ctx:SWIRLParser.PredContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#exec.
    def visitExec(self, ctx:SWIRLParser.ExecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#send.
    def visitSend(self, ctx:SWIRLParser.SendContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#recv.
    def visitRecv(self, ctx:SWIRLParser.RecvContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#dataPair.
    def visitDataPair(self, ctx:SWIRLParser.DataPairContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#dataSet.
    def visitDataSet(self, ctx:SWIRLParser.DataSetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#flow.
    def visitFlow(self, ctx:SWIRLParser.FlowContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#mapping.
    def visitMapping(self, ctx:SWIRLParser.MappingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#data.
    def visitData(self, ctx:SWIRLParser.DataContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#dst.
    def visitDst(self, ctx:SWIRLParser.DstContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#name.
    def visitName(self, ctx:SWIRLParser.NameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#port.
    def visitPort(self, ctx:SWIRLParser.PortContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#src.
    def visitSrc(self, ctx:SWIRLParser.SrcContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SWIRLParser#step.
    def visitStep(self, ctx:SWIRLParser.StepContext):
        return self.visitChildren(ctx)



del SWIRLParser