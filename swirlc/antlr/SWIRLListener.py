# Generated from /swirlc/grammar/SWIRL.g4 by ANTLR 4.13.1
from antlr4 import *
if "." in __name__:
    from .SWIRLParser import SWIRLParser
else:
    from SWIRLParser import SWIRLParser

# This class defines a complete listener for a parse tree produced by SWIRLParser.
class SWIRLListener(ParseTreeListener):

    # Enter a parse tree produced by SWIRLParser#workflow.
    def enterWorkflow(self, ctx:SWIRLParser.WorkflowContext):
        pass

    # Exit a parse tree produced by SWIRLParser#workflow.
    def exitWorkflow(self, ctx:SWIRLParser.WorkflowContext):
        pass


    # Enter a parse tree produced by SWIRLParser#location.
    def enterLocation(self, ctx:SWIRLParser.LocationContext):
        pass

    # Exit a parse tree produced by SWIRLParser#location.
    def exitLocation(self, ctx:SWIRLParser.LocationContext):
        pass


    # Enter a parse tree produced by SWIRLParser#TraceParen.
    def enterTraceParen(self, ctx:SWIRLParser.TraceParenContext):
        pass

    # Exit a parse tree produced by SWIRLParser#TraceParen.
    def exitTraceParen(self, ctx:SWIRLParser.TraceParenContext):
        pass


    # Enter a parse tree produced by SWIRLParser#TracePred.
    def enterTracePred(self, ctx:SWIRLParser.TracePredContext):
        pass

    # Exit a parse tree produced by SWIRLParser#TracePred.
    def exitTracePred(self, ctx:SWIRLParser.TracePredContext):
        pass


    # Enter a parse tree produced by SWIRLParser#TraceOp.
    def enterTraceOp(self, ctx:SWIRLParser.TraceOpContext):
        pass

    # Exit a parse tree produced by SWIRLParser#TraceOp.
    def exitTraceOp(self, ctx:SWIRLParser.TraceOpContext):
        pass


    # Enter a parse tree produced by SWIRLParser#pred.
    def enterPred(self, ctx:SWIRLParser.PredContext):
        pass

    # Exit a parse tree produced by SWIRLParser#pred.
    def exitPred(self, ctx:SWIRLParser.PredContext):
        pass


    # Enter a parse tree produced by SWIRLParser#exec.
    def enterExec(self, ctx:SWIRLParser.ExecContext):
        pass

    # Exit a parse tree produced by SWIRLParser#exec.
    def exitExec(self, ctx:SWIRLParser.ExecContext):
        pass


    # Enter a parse tree produced by SWIRLParser#send.
    def enterSend(self, ctx:SWIRLParser.SendContext):
        pass

    # Exit a parse tree produced by SWIRLParser#send.
    def exitSend(self, ctx:SWIRLParser.SendContext):
        pass


    # Enter a parse tree produced by SWIRLParser#recv.
    def enterRecv(self, ctx:SWIRLParser.RecvContext):
        pass

    # Exit a parse tree produced by SWIRLParser#recv.
    def exitRecv(self, ctx:SWIRLParser.RecvContext):
        pass


    # Enter a parse tree produced by SWIRLParser#dataPair.
    def enterDataPair(self, ctx:SWIRLParser.DataPairContext):
        pass

    # Exit a parse tree produced by SWIRLParser#dataPair.
    def exitDataPair(self, ctx:SWIRLParser.DataPairContext):
        pass


    # Enter a parse tree produced by SWIRLParser#dataSet.
    def enterDataSet(self, ctx:SWIRLParser.DataSetContext):
        pass

    # Exit a parse tree produced by SWIRLParser#dataSet.
    def exitDataSet(self, ctx:SWIRLParser.DataSetContext):
        pass


    # Enter a parse tree produced by SWIRLParser#flow.
    def enterFlow(self, ctx:SWIRLParser.FlowContext):
        pass

    # Exit a parse tree produced by SWIRLParser#flow.
    def exitFlow(self, ctx:SWIRLParser.FlowContext):
        pass


    # Enter a parse tree produced by SWIRLParser#mapping.
    def enterMapping(self, ctx:SWIRLParser.MappingContext):
        pass

    # Exit a parse tree produced by SWIRLParser#mapping.
    def exitMapping(self, ctx:SWIRLParser.MappingContext):
        pass


    # Enter a parse tree produced by SWIRLParser#data.
    def enterData(self, ctx:SWIRLParser.DataContext):
        pass

    # Exit a parse tree produced by SWIRLParser#data.
    def exitData(self, ctx:SWIRLParser.DataContext):
        pass


    # Enter a parse tree produced by SWIRLParser#dst.
    def enterDst(self, ctx:SWIRLParser.DstContext):
        pass

    # Exit a parse tree produced by SWIRLParser#dst.
    def exitDst(self, ctx:SWIRLParser.DstContext):
        pass


    # Enter a parse tree produced by SWIRLParser#name.
    def enterName(self, ctx:SWIRLParser.NameContext):
        pass

    # Exit a parse tree produced by SWIRLParser#name.
    def exitName(self, ctx:SWIRLParser.NameContext):
        pass


    # Enter a parse tree produced by SWIRLParser#port.
    def enterPort(self, ctx:SWIRLParser.PortContext):
        pass

    # Exit a parse tree produced by SWIRLParser#port.
    def exitPort(self, ctx:SWIRLParser.PortContext):
        pass


    # Enter a parse tree produced by SWIRLParser#src.
    def enterSrc(self, ctx:SWIRLParser.SrcContext):
        pass

    # Exit a parse tree produced by SWIRLParser#src.
    def exitSrc(self, ctx:SWIRLParser.SrcContext):
        pass


    # Enter a parse tree produced by SWIRLParser#step.
    def enterStep(self, ctx:SWIRLParser.StepContext):
        pass

    # Exit a parse tree produced by SWIRLParser#step.
    def exitStep(self, ctx:SWIRLParser.StepContext):
        pass



del SWIRLParser