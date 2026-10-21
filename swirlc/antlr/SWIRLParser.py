# Generated from grammar/SWIRL.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,31,247,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,1,0,1,0,1,0,5,0,46,8,0,10,0,12,0,49,9,0,1,0,1,0,1,1,1,1,1,1,
        1,1,1,1,1,1,1,1,1,1,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,3,2,70,8,
        2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,3,2,81,8,2,1,2,5,2,84,8,2,
        10,2,12,2,87,9,2,1,3,1,3,1,3,1,3,3,3,93,8,3,1,4,1,4,1,4,1,4,1,4,
        1,4,1,4,1,4,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,6,1,6,1,6,
        1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,
        1,7,1,8,1,8,1,8,1,8,1,8,1,8,3,8,139,8,8,1,8,1,8,1,9,1,9,1,9,1,9,
        1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,3,9,156,8,9,1,10,1,10,1,10,1,
        10,1,10,1,10,1,10,1,10,1,10,1,10,1,11,1,11,3,11,170,8,11,1,11,1,
        11,5,11,174,8,11,10,11,12,11,177,9,11,1,11,1,11,1,12,1,12,1,12,1,
        12,1,13,1,13,3,13,187,8,13,1,13,1,13,5,13,191,8,13,10,13,12,13,194,
        9,13,1,13,1,13,3,13,198,8,13,1,14,1,14,1,15,1,15,1,15,1,15,1,15,
        1,15,1,15,3,15,209,8,15,1,15,1,15,1,15,1,15,1,15,1,15,1,15,1,15,
        1,15,5,15,220,8,15,10,15,12,15,223,9,15,1,15,1,15,3,15,227,8,15,
        1,15,1,15,1,15,5,15,232,8,15,10,15,12,15,235,9,15,1,16,1,16,1,17,
        1,17,1,18,1,18,1,19,1,19,1,20,1,20,1,20,0,2,4,30,21,0,2,4,6,8,10,
        12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,0,0,252,0,42,1,0,0,
        0,2,52,1,0,0,0,4,69,1,0,0,0,6,92,1,0,0,0,8,94,1,0,0,0,10,102,1,0,
        0,0,12,112,1,0,0,0,14,122,1,0,0,0,16,132,1,0,0,0,18,155,1,0,0,0,
        20,157,1,0,0,0,22,167,1,0,0,0,24,180,1,0,0,0,26,197,1,0,0,0,28,199,
        1,0,0,0,30,226,1,0,0,0,32,236,1,0,0,0,34,238,1,0,0,0,36,240,1,0,
        0,0,38,242,1,0,0,0,40,244,1,0,0,0,42,47,3,2,1,0,43,44,5,22,0,0,44,
        46,3,2,1,0,45,43,1,0,0,0,46,49,1,0,0,0,47,45,1,0,0,0,47,48,1,0,0,
        0,48,50,1,0,0,0,49,47,1,0,0,0,50,51,5,0,0,1,51,1,1,0,0,0,52,53,5,
        1,0,0,53,54,3,34,17,0,54,55,5,2,0,0,55,56,3,22,11,0,56,57,5,2,0,
        0,57,58,3,4,2,0,58,59,5,3,0,0,59,3,1,0,0,0,60,61,6,2,-1,0,61,62,
        5,20,0,0,62,70,3,4,2,7,63,70,3,6,3,0,64,70,5,27,0,0,65,66,5,4,0,
        0,66,67,3,4,2,0,67,68,5,5,0,0,68,70,1,0,0,0,69,60,1,0,0,0,69,63,
        1,0,0,0,69,64,1,0,0,0,69,65,1,0,0,0,70,85,1,0,0,0,71,72,10,6,0,0,
        72,73,5,23,0,0,73,84,3,4,2,7,74,75,10,5,0,0,75,76,5,22,0,0,76,84,
        3,4,2,6,77,78,10,4,0,0,78,80,5,21,0,0,79,81,3,16,8,0,80,79,1,0,0,
        0,80,81,1,0,0,0,81,82,1,0,0,0,82,84,3,4,2,5,83,71,1,0,0,0,83,74,
        1,0,0,0,83,77,1,0,0,0,84,87,1,0,0,0,85,83,1,0,0,0,85,86,1,0,0,0,
        86,5,1,0,0,0,87,85,1,0,0,0,88,93,3,8,4,0,89,93,3,10,5,0,90,93,3,
        12,6,0,91,93,3,14,7,0,92,88,1,0,0,0,92,89,1,0,0,0,92,90,1,0,0,0,
        92,91,1,0,0,0,93,7,1,0,0,0,94,95,5,6,0,0,95,96,3,40,20,0,96,97,5,
        2,0,0,97,98,3,24,12,0,98,99,5,2,0,0,99,100,3,28,14,0,100,101,5,5,
        0,0,101,9,1,0,0,0,102,103,5,7,0,0,103,104,3,30,15,0,104,105,5,8,
        0,0,105,106,3,36,18,0,106,107,5,2,0,0,107,108,3,38,19,0,108,109,
        5,2,0,0,109,110,3,32,16,0,110,111,5,5,0,0,111,11,1,0,0,0,112,113,
        5,9,0,0,113,114,3,30,15,0,114,115,5,8,0,0,115,116,3,36,18,0,116,
        117,5,2,0,0,117,118,3,38,19,0,118,119,5,2,0,0,119,120,3,32,16,0,
        120,121,5,5,0,0,121,13,1,0,0,0,122,123,5,10,0,0,123,124,3,30,15,
        0,124,125,5,8,0,0,125,126,3,36,18,0,126,127,5,2,0,0,127,128,3,38,
        19,0,128,129,5,2,0,0,129,130,3,32,16,0,130,131,5,5,0,0,131,15,1,
        0,0,0,132,133,5,11,0,0,133,138,3,36,18,0,134,135,5,12,0,0,135,136,
        5,13,0,0,136,137,5,26,0,0,137,139,3,30,15,0,138,134,1,0,0,0,138,
        139,1,0,0,0,139,140,1,0,0,0,140,141,5,14,0,0,141,17,1,0,0,0,142,
        143,5,4,0,0,143,144,3,36,18,0,144,145,5,2,0,0,145,146,3,30,15,0,
        146,147,5,5,0,0,147,156,1,0,0,0,148,149,5,4,0,0,149,150,3,30,15,
        0,150,151,5,2,0,0,151,152,3,36,18,0,152,153,5,5,0,0,153,156,1,0,
        0,0,154,156,3,20,10,0,155,142,1,0,0,0,155,148,1,0,0,0,155,154,1,
        0,0,0,156,19,1,0,0,0,157,158,5,15,0,0,158,159,3,36,18,0,159,160,
        5,2,0,0,160,161,5,4,0,0,161,162,3,34,17,0,162,163,5,2,0,0,163,164,
        3,30,15,0,164,165,5,5,0,0,165,166,5,5,0,0,166,21,1,0,0,0,167,169,
        5,16,0,0,168,170,3,18,9,0,169,168,1,0,0,0,169,170,1,0,0,0,170,175,
        1,0,0,0,171,172,5,2,0,0,172,174,3,18,9,0,173,171,1,0,0,0,174,177,
        1,0,0,0,175,173,1,0,0,0,175,176,1,0,0,0,176,178,1,0,0,0,177,175,
        1,0,0,0,178,179,5,17,0,0,179,23,1,0,0,0,180,181,3,22,11,0,181,182,
        5,8,0,0,182,183,3,22,11,0,183,25,1,0,0,0,184,186,5,16,0,0,185,187,
        3,34,17,0,186,185,1,0,0,0,186,187,1,0,0,0,187,192,1,0,0,0,188,189,
        5,2,0,0,189,191,3,34,17,0,190,188,1,0,0,0,191,194,1,0,0,0,192,190,
        1,0,0,0,192,193,1,0,0,0,193,195,1,0,0,0,194,192,1,0,0,0,195,198,
        5,17,0,0,196,198,5,28,0,0,197,184,1,0,0,0,197,196,1,0,0,0,198,27,
        1,0,0,0,199,200,3,26,13,0,200,29,1,0,0,0,201,202,6,15,-1,0,202,203,
        5,19,0,0,203,227,5,28,0,0,204,208,5,28,0,0,205,206,5,11,0,0,206,
        207,5,28,0,0,207,209,5,14,0,0,208,205,1,0,0,0,208,209,1,0,0,0,209,
        227,1,0,0,0,210,227,5,27,0,0,211,227,5,24,0,0,212,227,5,25,0,0,213,
        214,5,4,0,0,214,215,3,30,15,0,215,216,5,2,0,0,216,221,3,30,15,0,
        217,218,5,2,0,0,218,220,3,30,15,0,219,217,1,0,0,0,220,223,1,0,0,
        0,221,219,1,0,0,0,221,222,1,0,0,0,222,224,1,0,0,0,223,221,1,0,0,
        0,224,225,5,5,0,0,225,227,1,0,0,0,226,201,1,0,0,0,226,204,1,0,0,
        0,226,210,1,0,0,0,226,211,1,0,0,0,226,212,1,0,0,0,226,213,1,0,0,
        0,227,233,1,0,0,0,228,229,10,7,0,0,229,230,5,18,0,0,230,232,3,30,
        15,8,231,228,1,0,0,0,232,235,1,0,0,0,233,231,1,0,0,0,233,234,1,0,
        0,0,234,31,1,0,0,0,235,233,1,0,0,0,236,237,3,26,13,0,237,33,1,0,
        0,0,238,239,5,28,0,0,239,35,1,0,0,0,240,241,5,28,0,0,241,37,1,0,
        0,0,242,243,5,28,0,0,243,39,1,0,0,0,244,245,5,28,0,0,245,41,1,0,
        0,0,17,47,69,80,83,85,92,138,155,169,175,186,192,197,208,221,226,
        233
    ]

class SWIRLParser ( Parser ):

    grammarFileName = "SWIRL.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'<'", "','", "'>'", "'('", "')'", "'exec('",
                     "'send('", "'->'", "'recv('", "'move('", "'['", "'has'",
                     "'data'", "']'", "'U('", "'{'", "'}'", "'/'", "'?'",
                     "'!'", "'+'", "'|'", "'.'", "'eof'", "'begin'", "'in'",
                     "'0'" ]

    symbolicNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>",
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>",
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>",
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>",
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>",
                      "REPL", "CHOICE", "PAR", "SEQ", "EOF_VAL", "BEGIN_VAL",
                      "IN", "ZERO", "ID", "WS", "COMMENT", "BLOCK_COMMENT" ]

    RULE_workflow = 0
    RULE_location = 1
    RULE_trace = 2
    RULE_pred = 3
    RULE_exec = 4
    RULE_send = 5
    RULE_recv = 6
    RULE_move = 7
    RULE_guard = 8
    RULE_dataPair = 9
    RULE_collection = 10
    RULE_dataSet = 11
    RULE_flow = 12
    RULE_locationSet = 13
    RULE_mapping = 14
    RULE_data = 15
    RULE_dst = 16
    RULE_name = 17
    RULE_port = 18
    RULE_src = 19
    RULE_step = 20

    ruleNames =  [ "workflow", "location", "trace", "pred", "exec", "send",
                   "recv", "move", "guard", "dataPair", "collection", "dataSet",
                   "flow", "locationSet", "mapping", "data", "dst", "name",
                   "port", "src", "step" ]

    EOF = Token.EOF
    T__0=1
    T__1=2
    T__2=3
    T__3=4
    T__4=5
    T__5=6
    T__6=7
    T__7=8
    T__8=9
    T__9=10
    T__10=11
    T__11=12
    T__12=13
    T__13=14
    T__14=15
    T__15=16
    T__16=17
    T__17=18
    T__18=19
    REPL=20
    CHOICE=21
    PAR=22
    SEQ=23
    EOF_VAL=24
    BEGIN_VAL=25
    IN=26
    ZERO=27
    ID=28
    WS=29
    COMMENT=30
    BLOCK_COMMENT=31

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class WorkflowContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def location(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SWIRLParser.LocationContext)
            else:
                return self.getTypedRuleContext(SWIRLParser.LocationContext,i)


        def EOF(self):
            return self.getToken(SWIRLParser.EOF, 0)

        def PAR(self, i:int=None):
            if i is None:
                return self.getTokens(SWIRLParser.PAR)
            else:
                return self.getToken(SWIRLParser.PAR, i)

        def getRuleIndex(self):
            return SWIRLParser.RULE_workflow

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterWorkflow" ):
                listener.enterWorkflow(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitWorkflow" ):
                listener.exitWorkflow(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitWorkflow" ):
                return visitor.visitWorkflow(self)
            else:
                return visitor.visitChildren(self)




    def workflow(self):

        localctx = SWIRLParser.WorkflowContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_workflow)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 42
            self.location()
            self.state = 47
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==22:
                self.state = 43
                self.match(SWIRLParser.PAR)
                self.state = 44
                self.location()
                self.state = 49
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 50
            self.match(SWIRLParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LocationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name(self):
            return self.getTypedRuleContext(SWIRLParser.NameContext,0)


        def dataSet(self):
            return self.getTypedRuleContext(SWIRLParser.DataSetContext,0)


        def trace(self):
            return self.getTypedRuleContext(SWIRLParser.TraceContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_location

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLocation" ):
                listener.enterLocation(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLocation" ):
                listener.exitLocation(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLocation" ):
                return visitor.visitLocation(self)
            else:
                return visitor.visitChildren(self)




    def location(self):

        localctx = SWIRLParser.LocationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_location)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 52
            self.match(SWIRLParser.T__0)
            self.state = 53
            self.name()
            self.state = 54
            self.match(SWIRLParser.T__1)
            self.state = 55
            self.dataSet()
            self.state = 56
            self.match(SWIRLParser.T__1)
            self.state = 57
            self.trace(0)
            self.state = 58
            self.match(SWIRLParser.T__2)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TraceContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return SWIRLParser.RULE_trace


        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class TraceReplContext(TraceContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SWIRLParser.TraceContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def REPL(self):
            return self.getToken(SWIRLParser.REPL, 0)
        def trace(self):
            return self.getTypedRuleContext(SWIRLParser.TraceContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTraceRepl" ):
                listener.enterTraceRepl(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTraceRepl" ):
                listener.exitTraceRepl(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTraceRepl" ):
                return visitor.visitTraceRepl(self)
            else:
                return visitor.visitChildren(self)


    class TraceParenContext(TraceContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SWIRLParser.TraceContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def trace(self):
            return self.getTypedRuleContext(SWIRLParser.TraceContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTraceParen" ):
                listener.enterTraceParen(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTraceParen" ):
                listener.exitTraceParen(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTraceParen" ):
                return visitor.visitTraceParen(self)
            else:
                return visitor.visitChildren(self)


    class TracePredContext(TraceContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SWIRLParser.TraceContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def pred(self):
            return self.getTypedRuleContext(SWIRLParser.PredContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTracePred" ):
                listener.enterTracePred(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTracePred" ):
                listener.exitTracePred(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTracePred" ):
                return visitor.visitTracePred(self)
            else:
                return visitor.visitChildren(self)


    class TraceZeroContext(TraceContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SWIRLParser.TraceContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ZERO(self):
            return self.getToken(SWIRLParser.ZERO, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTraceZero" ):
                listener.enterTraceZero(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTraceZero" ):
                listener.exitTraceZero(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTraceZero" ):
                return visitor.visitTraceZero(self)
            else:
                return visitor.visitChildren(self)


    class TraceOpContext(TraceContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SWIRLParser.TraceContext
            super().__init__(parser)
            self.op = None # Token
            self.copyFrom(ctx)

        def trace(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SWIRLParser.TraceContext)
            else:
                return self.getTypedRuleContext(SWIRLParser.TraceContext,i)

        def SEQ(self):
            return self.getToken(SWIRLParser.SEQ, 0)
        def PAR(self):
            return self.getToken(SWIRLParser.PAR, 0)
        def CHOICE(self):
            return self.getToken(SWIRLParser.CHOICE, 0)
        def guard(self):
            return self.getTypedRuleContext(SWIRLParser.GuardContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTraceOp" ):
                listener.enterTraceOp(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTraceOp" ):
                listener.exitTraceOp(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTraceOp" ):
                return visitor.visitTraceOp(self)
            else:
                return visitor.visitChildren(self)



    def trace(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = SWIRLParser.TraceContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 4
        self.enterRecursionRule(localctx, 4, self.RULE_trace, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 69
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [20]:
                localctx = SWIRLParser.TraceReplContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 61
                self.match(SWIRLParser.REPL)
                self.state = 62
                self.trace(7)
                pass
            elif token in [6, 7, 9, 10]:
                localctx = SWIRLParser.TracePredContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 63
                self.pred()
                pass
            elif token in [27]:
                localctx = SWIRLParser.TraceZeroContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 64
                self.match(SWIRLParser.ZERO)
                pass
            elif token in [4]:
                localctx = SWIRLParser.TraceParenContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 65
                self.match(SWIRLParser.T__3)
                self.state = 66
                self.trace(0)
                self.state = 67
                self.match(SWIRLParser.T__4)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 85
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,4,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 83
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,3,self._ctx)
                    if la_ == 1:
                        localctx = SWIRLParser.TraceOpContext(self, SWIRLParser.TraceContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_trace)
                        self.state = 71
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 72
                        localctx.op = self.match(SWIRLParser.SEQ)
                        self.state = 73
                        self.trace(7)
                        pass

                    elif la_ == 2:
                        localctx = SWIRLParser.TraceOpContext(self, SWIRLParser.TraceContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_trace)
                        self.state = 74
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 75
                        localctx.op = self.match(SWIRLParser.PAR)
                        self.state = 76
                        self.trace(6)
                        pass

                    elif la_ == 3:
                        localctx = SWIRLParser.TraceOpContext(self, SWIRLParser.TraceContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_trace)
                        self.state = 77
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 78
                        localctx.op = self.match(SWIRLParser.CHOICE)
                        self.state = 80
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if _la==11:
                            self.state = 79
                            self.guard()


                        self.state = 82
                        self.trace(5)
                        pass


                self.state = 87
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,4,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class PredContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def exec(self):
            return self.getTypedRuleContext(SWIRLParser.ExecContext,0)


        def send(self):
            return self.getTypedRuleContext(SWIRLParser.SendContext,0)


        def recv(self):
            return self.getTypedRuleContext(SWIRLParser.RecvContext,0)


        def move(self):
            return self.getTypedRuleContext(SWIRLParser.MoveContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_pred

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPred" ):
                listener.enterPred(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPred" ):
                listener.exitPred(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPred" ):
                return visitor.visitPred(self)
            else:
                return visitor.visitChildren(self)




    def pred(self):

        localctx = SWIRLParser.PredContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_pred)
        try:
            self.state = 92
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6]:
                self.enterOuterAlt(localctx, 1)
                self.state = 88
                self.exec()
                pass
            elif token in [7]:
                self.enterOuterAlt(localctx, 2)
                self.state = 89
                self.send()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 3)
                self.state = 90
                self.recv()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 4)
                self.state = 91
                self.move()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def step(self):
            return self.getTypedRuleContext(SWIRLParser.StepContext,0)


        def flow(self):
            return self.getTypedRuleContext(SWIRLParser.FlowContext,0)


        def mapping(self):
            return self.getTypedRuleContext(SWIRLParser.MappingContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_exec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExec" ):
                listener.enterExec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExec" ):
                listener.exitExec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExec" ):
                return visitor.visitExec(self)
            else:
                return visitor.visitChildren(self)




    def exec(self):

        localctx = SWIRLParser.ExecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_exec)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 94
            self.match(SWIRLParser.T__5)
            self.state = 95
            self.step()
            self.state = 96
            self.match(SWIRLParser.T__1)
            self.state = 97
            self.flow()
            self.state = 98
            self.match(SWIRLParser.T__1)
            self.state = 99
            self.mapping()
            self.state = 100
            self.match(SWIRLParser.T__4)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SendContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def data(self):
            return self.getTypedRuleContext(SWIRLParser.DataContext,0)


        def port(self):
            return self.getTypedRuleContext(SWIRLParser.PortContext,0)


        def src(self):
            return self.getTypedRuleContext(SWIRLParser.SrcContext,0)


        def dst(self):
            return self.getTypedRuleContext(SWIRLParser.DstContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_send

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSend" ):
                listener.enterSend(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSend" ):
                listener.exitSend(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSend" ):
                return visitor.visitSend(self)
            else:
                return visitor.visitChildren(self)




    def send(self):

        localctx = SWIRLParser.SendContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_send)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 102
            self.match(SWIRLParser.T__6)
            self.state = 103
            self.data(0)
            self.state = 104
            self.match(SWIRLParser.T__7)
            self.state = 105
            self.port()
            self.state = 106
            self.match(SWIRLParser.T__1)
            self.state = 107
            self.src()
            self.state = 108
            self.match(SWIRLParser.T__1)
            self.state = 109
            self.dst()
            self.state = 110
            self.match(SWIRLParser.T__4)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RecvContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def data(self):
            return self.getTypedRuleContext(SWIRLParser.DataContext,0)


        def port(self):
            return self.getTypedRuleContext(SWIRLParser.PortContext,0)


        def src(self):
            return self.getTypedRuleContext(SWIRLParser.SrcContext,0)


        def dst(self):
            return self.getTypedRuleContext(SWIRLParser.DstContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_recv

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRecv" ):
                listener.enterRecv(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRecv" ):
                listener.exitRecv(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRecv" ):
                return visitor.visitRecv(self)
            else:
                return visitor.visitChildren(self)




    def recv(self):

        localctx = SWIRLParser.RecvContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_recv)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 112
            self.match(SWIRLParser.T__8)
            self.state = 113
            self.data(0)
            self.state = 114
            self.match(SWIRLParser.T__7)
            self.state = 115
            self.port()
            self.state = 116
            self.match(SWIRLParser.T__1)
            self.state = 117
            self.src()
            self.state = 118
            self.match(SWIRLParser.T__1)
            self.state = 119
            self.dst()
            self.state = 120
            self.match(SWIRLParser.T__4)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MoveContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def data(self):
            return self.getTypedRuleContext(SWIRLParser.DataContext,0)


        def port(self):
            return self.getTypedRuleContext(SWIRLParser.PortContext,0)


        def src(self):
            return self.getTypedRuleContext(SWIRLParser.SrcContext,0)


        def dst(self):
            return self.getTypedRuleContext(SWIRLParser.DstContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_move

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterMove" ):
                listener.enterMove(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitMove" ):
                listener.exitMove(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMove" ):
                return visitor.visitMove(self)
            else:
                return visitor.visitChildren(self)




    def move(self):

        localctx = SWIRLParser.MoveContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_move)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 122
            self.match(SWIRLParser.T__9)
            self.state = 123
            self.data(0)
            self.state = 124
            self.match(SWIRLParser.T__7)
            self.state = 125
            self.port()
            self.state = 126
            self.match(SWIRLParser.T__1)
            self.state = 127
            self.src()
            self.state = 128
            self.match(SWIRLParser.T__1)
            self.state = 129
            self.dst()
            self.state = 130
            self.match(SWIRLParser.T__4)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GuardContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def port(self):
            return self.getTypedRuleContext(SWIRLParser.PortContext,0)


        def IN(self):
            return self.getToken(SWIRLParser.IN, 0)

        def data(self):
            return self.getTypedRuleContext(SWIRLParser.DataContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_guard

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterGuard" ):
                listener.enterGuard(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitGuard" ):
                listener.exitGuard(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGuard" ):
                return visitor.visitGuard(self)
            else:
                return visitor.visitChildren(self)




    def guard(self):

        localctx = SWIRLParser.GuardContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_guard)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 132
            self.match(SWIRLParser.T__10)
            self.state = 133
            self.port()
            self.state = 138
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 134
                self.match(SWIRLParser.T__11)
                self.state = 135
                self.match(SWIRLParser.T__12)
                self.state = 136
                self.match(SWIRLParser.IN)
                self.state = 137
                self.data(0)


            self.state = 140
            self.match(SWIRLParser.T__13)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DataPairContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def port(self):
            return self.getTypedRuleContext(SWIRLParser.PortContext,0)


        def data(self):
            return self.getTypedRuleContext(SWIRLParser.DataContext,0)


        def collection(self):
            return self.getTypedRuleContext(SWIRLParser.CollectionContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_dataPair

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDataPair" ):
                listener.enterDataPair(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDataPair" ):
                listener.exitDataPair(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDataPair" ):
                return visitor.visitDataPair(self)
            else:
                return visitor.visitChildren(self)




    def dataPair(self):

        localctx = SWIRLParser.DataPairContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_dataPair)
        try:
            self.state = 155
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,7,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 142
                self.match(SWIRLParser.T__3)
                self.state = 143
                self.port()
                self.state = 144
                self.match(SWIRLParser.T__1)
                self.state = 145
                self.data(0)
                self.state = 146
                self.match(SWIRLParser.T__4)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 148
                self.match(SWIRLParser.T__3)
                self.state = 149
                self.data(0)
                self.state = 150
                self.match(SWIRLParser.T__1)
                self.state = 151
                self.port()
                self.state = 152
                self.match(SWIRLParser.T__4)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 154
                self.collection()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CollectionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def port(self):
            return self.getTypedRuleContext(SWIRLParser.PortContext,0)


        def name(self):
            return self.getTypedRuleContext(SWIRLParser.NameContext,0)


        def data(self):
            return self.getTypedRuleContext(SWIRLParser.DataContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_collection

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCollection" ):
                listener.enterCollection(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCollection" ):
                listener.exitCollection(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCollection" ):
                return visitor.visitCollection(self)
            else:
                return visitor.visitChildren(self)




    def collection(self):

        localctx = SWIRLParser.CollectionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_collection)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 157
            self.match(SWIRLParser.T__14)
            self.state = 158
            self.port()
            self.state = 159
            self.match(SWIRLParser.T__1)
            self.state = 160
            self.match(SWIRLParser.T__3)
            self.state = 161
            self.name()
            self.state = 162
            self.match(SWIRLParser.T__1)
            self.state = 163
            self.data(0)
            self.state = 164
            self.match(SWIRLParser.T__4)
            self.state = 165
            self.match(SWIRLParser.T__4)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DataSetContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def dataPair(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SWIRLParser.DataPairContext)
            else:
                return self.getTypedRuleContext(SWIRLParser.DataPairContext,i)


        def getRuleIndex(self):
            return SWIRLParser.RULE_dataSet

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDataSet" ):
                listener.enterDataSet(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDataSet" ):
                listener.exitDataSet(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDataSet" ):
                return visitor.visitDataSet(self)
            else:
                return visitor.visitChildren(self)




    def dataSet(self):

        localctx = SWIRLParser.DataSetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_dataSet)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 167
            self.match(SWIRLParser.T__15)
            self.state = 169
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==4 or _la==15:
                self.state = 168
                self.dataPair()


            self.state = 175
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==2:
                self.state = 171
                self.match(SWIRLParser.T__1)
                self.state = 172
                self.dataPair()
                self.state = 177
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 178
            self.match(SWIRLParser.T__16)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FlowContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def dataSet(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SWIRLParser.DataSetContext)
            else:
                return self.getTypedRuleContext(SWIRLParser.DataSetContext,i)


        def getRuleIndex(self):
            return SWIRLParser.RULE_flow

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterFlow" ):
                listener.enterFlow(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitFlow" ):
                listener.exitFlow(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFlow" ):
                return visitor.visitFlow(self)
            else:
                return visitor.visitChildren(self)




    def flow(self):

        localctx = SWIRLParser.FlowContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_flow)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 180
            self.dataSet()
            self.state = 181
            self.match(SWIRLParser.T__7)
            self.state = 182
            self.dataSet()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LocationSetContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SWIRLParser.NameContext)
            else:
                return self.getTypedRuleContext(SWIRLParser.NameContext,i)


        def ID(self):
            return self.getToken(SWIRLParser.ID, 0)

        def getRuleIndex(self):
            return SWIRLParser.RULE_locationSet

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLocationSet" ):
                listener.enterLocationSet(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLocationSet" ):
                listener.exitLocationSet(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLocationSet" ):
                return visitor.visitLocationSet(self)
            else:
                return visitor.visitChildren(self)




    def locationSet(self):

        localctx = SWIRLParser.LocationSetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_locationSet)
        self._la = 0 # Token type
        try:
            self.state = 197
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [16]:
                self.enterOuterAlt(localctx, 1)
                self.state = 184
                self.match(SWIRLParser.T__15)
                self.state = 186
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==28:
                    self.state = 185
                    self.name()


                self.state = 192
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==2:
                    self.state = 188
                    self.match(SWIRLParser.T__1)
                    self.state = 189
                    self.name()
                    self.state = 194
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 195
                self.match(SWIRLParser.T__16)
                pass
            elif token in [28]:
                self.enterOuterAlt(localctx, 2)
                self.state = 196
                self.match(SWIRLParser.ID)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MappingContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def locationSet(self):
            return self.getTypedRuleContext(SWIRLParser.LocationSetContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_mapping

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterMapping" ):
                listener.enterMapping(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitMapping" ):
                listener.exitMapping(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMapping" ):
                return visitor.visitMapping(self)
            else:
                return visitor.visitChildren(self)




    def mapping(self):

        localctx = SWIRLParser.MappingContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_mapping)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 199
            self.locationSet()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DataContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self, i:int=None):
            if i is None:
                return self.getTokens(SWIRLParser.ID)
            else:
                return self.getToken(SWIRLParser.ID, i)

        def ZERO(self):
            return self.getToken(SWIRLParser.ZERO, 0)

        def EOF_VAL(self):
            return self.getToken(SWIRLParser.EOF_VAL, 0)

        def BEGIN_VAL(self):
            return self.getToken(SWIRLParser.BEGIN_VAL, 0)

        def data(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SWIRLParser.DataContext)
            else:
                return self.getTypedRuleContext(SWIRLParser.DataContext,i)


        def getRuleIndex(self):
            return SWIRLParser.RULE_data

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterData" ):
                listener.enterData(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitData" ):
                listener.exitData(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitData" ):
                return visitor.visitData(self)
            else:
                return visitor.visitChildren(self)



    def data(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = SWIRLParser.DataContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 30
        self.enterRecursionRule(localctx, 30, self.RULE_data, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 226
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [19]:
                self.state = 202
                self.match(SWIRLParser.T__18)
                self.state = 203
                self.match(SWIRLParser.ID)
                pass
            elif token in [28]:
                self.state = 204
                self.match(SWIRLParser.ID)
                self.state = 208
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
                if la_ == 1:
                    self.state = 205
                    self.match(SWIRLParser.T__10)
                    self.state = 206
                    self.match(SWIRLParser.ID)
                    self.state = 207
                    self.match(SWIRLParser.T__13)


                pass
            elif token in [27]:
                self.state = 210
                self.match(SWIRLParser.ZERO)
                pass
            elif token in [24]:
                self.state = 211
                self.match(SWIRLParser.EOF_VAL)
                pass
            elif token in [25]:
                self.state = 212
                self.match(SWIRLParser.BEGIN_VAL)
                pass
            elif token in [4]:
                self.state = 213
                self.match(SWIRLParser.T__3)
                self.state = 214
                self.data(0)
                self.state = 215
                self.match(SWIRLParser.T__1)
                self.state = 216
                self.data(0)
                self.state = 221
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==2:
                    self.state = 217
                    self.match(SWIRLParser.T__1)
                    self.state = 218
                    self.data(0)
                    self.state = 223
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 224
                self.match(SWIRLParser.T__4)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 233
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,16,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = SWIRLParser.DataContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_data)
                    self.state = 228
                    if not self.precpred(self._ctx, 7):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 7)")
                    self.state = 229
                    self.match(SWIRLParser.T__17)
                    self.state = 230
                    self.data(8)
                self.state = 235
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,16,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class DstContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def locationSet(self):
            return self.getTypedRuleContext(SWIRLParser.LocationSetContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_dst

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDst" ):
                listener.enterDst(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDst" ):
                listener.exitDst(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDst" ):
                return visitor.visitDst(self)
            else:
                return visitor.visitChildren(self)




    def dst(self):

        localctx = SWIRLParser.DstContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_dst)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 236
            self.locationSet()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(SWIRLParser.ID, 0)

        def getRuleIndex(self):
            return SWIRLParser.RULE_name

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterName" ):
                listener.enterName(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitName" ):
                listener.exitName(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitName" ):
                return visitor.visitName(self)
            else:
                return visitor.visitChildren(self)




    def name(self):

        localctx = SWIRLParser.NameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 238
            self.match(SWIRLParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PortContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(SWIRLParser.ID, 0)

        def getRuleIndex(self):
            return SWIRLParser.RULE_port

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPort" ):
                listener.enterPort(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPort" ):
                listener.exitPort(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPort" ):
                return visitor.visitPort(self)
            else:
                return visitor.visitChildren(self)




    def port(self):

        localctx = SWIRLParser.PortContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_port)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 240
            self.match(SWIRLParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SrcContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(SWIRLParser.ID, 0)

        def getRuleIndex(self):
            return SWIRLParser.RULE_src

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSrc" ):
                listener.enterSrc(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSrc" ):
                listener.exitSrc(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSrc" ):
                return visitor.visitSrc(self)
            else:
                return visitor.visitChildren(self)




    def src(self):

        localctx = SWIRLParser.SrcContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_src)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 242
            self.match(SWIRLParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StepContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(SWIRLParser.ID, 0)

        def getRuleIndex(self):
            return SWIRLParser.RULE_step

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStep" ):
                listener.enterStep(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStep" ):
                listener.exitStep(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStep" ):
                return visitor.visitStep(self)
            else:
                return visitor.visitChildren(self)




    def step(self):

        localctx = SWIRLParser.StepContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_step)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 244
            self.match(SWIRLParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx



    def sempred(self, localctx:RuleContext, ruleIndex:int, predIndex:int):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[2] = self.trace_sempred
        self._predicates[15] = self.data_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def trace_sempred(self, localctx:TraceContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 6)


            if predIndex == 1:
                return self.precpred(self._ctx, 5)


            if predIndex == 2:
                return self.precpred(self._ctx, 4)


    def data_sempred(self, localctx:DataContext, predIndex:int):
            if predIndex == 3:
                return self.precpred(self._ctx, 7)





