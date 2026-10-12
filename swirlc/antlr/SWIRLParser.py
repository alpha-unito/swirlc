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
        4,1,32,248,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,1,0,1,0,1,0,5,0,48,8,0,10,0,12,0,51,9,0,1,0,1,0,1,
        1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,
        2,3,2,72,8,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,3,2,83,8,2,1,2,
        5,2,86,8,2,10,2,12,2,89,9,2,1,3,1,3,1,3,1,3,1,3,3,3,96,8,3,1,4,1,
        4,1,4,1,4,1,4,1,4,1,4,1,4,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,
        5,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,7,1,7,1,7,1,7,1,7,1,
        7,1,7,1,7,1,7,1,7,1,8,1,8,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,10,1,
        10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,3,10,159,
        8,10,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,12,1,12,3,12,171,
        8,12,1,12,1,12,5,12,175,8,12,10,12,12,12,178,9,12,1,12,1,12,1,13,
        1,13,1,13,1,13,1,14,1,14,3,14,188,8,14,1,14,1,14,5,14,192,8,14,10,
        14,12,14,195,9,14,1,14,1,14,3,14,199,8,14,1,15,1,15,1,16,1,16,1,
        16,1,16,1,16,1,16,1,16,3,16,210,8,16,1,16,1,16,1,16,1,16,1,16,1,
        16,1,16,1,16,1,16,5,16,221,8,16,10,16,12,16,224,9,16,1,16,1,16,3,
        16,228,8,16,1,16,1,16,1,16,5,16,233,8,16,10,16,12,16,236,9,16,1,
        17,1,17,1,18,1,18,1,19,1,19,1,20,1,20,1,21,1,21,1,21,0,2,4,32,22,
        0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,0,0,
        252,0,44,1,0,0,0,2,54,1,0,0,0,4,71,1,0,0,0,6,95,1,0,0,0,8,97,1,0,
        0,0,10,105,1,0,0,0,12,115,1,0,0,0,14,125,1,0,0,0,16,135,1,0,0,0,
        18,137,1,0,0,0,20,158,1,0,0,0,22,160,1,0,0,0,24,168,1,0,0,0,26,181,
        1,0,0,0,28,198,1,0,0,0,30,200,1,0,0,0,32,227,1,0,0,0,34,237,1,0,
        0,0,36,239,1,0,0,0,38,241,1,0,0,0,40,243,1,0,0,0,42,245,1,0,0,0,
        44,49,3,2,1,0,45,46,5,23,0,0,46,48,3,2,1,0,47,45,1,0,0,0,48,51,1,
        0,0,0,49,47,1,0,0,0,49,50,1,0,0,0,50,52,1,0,0,0,51,49,1,0,0,0,52,
        53,5,0,0,1,53,1,1,0,0,0,54,55,5,1,0,0,55,56,3,36,18,0,56,57,5,2,
        0,0,57,58,3,24,12,0,58,59,5,2,0,0,59,60,3,4,2,0,60,61,5,3,0,0,61,
        3,1,0,0,0,62,63,6,2,-1,0,63,64,5,21,0,0,64,72,3,4,2,7,65,72,3,6,
        3,0,66,72,5,28,0,0,67,68,5,4,0,0,68,69,3,4,2,0,69,70,5,5,0,0,70,
        72,1,0,0,0,71,62,1,0,0,0,71,65,1,0,0,0,71,66,1,0,0,0,71,67,1,0,0,
        0,72,87,1,0,0,0,73,74,10,6,0,0,74,75,5,24,0,0,75,86,3,4,2,7,76,77,
        10,5,0,0,77,78,5,23,0,0,78,86,3,4,2,6,79,80,10,4,0,0,80,82,5,22,
        0,0,81,83,3,18,9,0,82,81,1,0,0,0,82,83,1,0,0,0,83,84,1,0,0,0,84,
        86,3,4,2,5,85,73,1,0,0,0,85,76,1,0,0,0,85,79,1,0,0,0,86,89,1,0,0,
        0,87,85,1,0,0,0,87,88,1,0,0,0,88,5,1,0,0,0,89,87,1,0,0,0,90,96,3,
        8,4,0,91,96,3,10,5,0,92,96,3,12,6,0,93,96,3,14,7,0,94,96,3,16,8,
        0,95,90,1,0,0,0,95,91,1,0,0,0,95,92,1,0,0,0,95,93,1,0,0,0,95,94,
        1,0,0,0,96,7,1,0,0,0,97,98,5,6,0,0,98,99,3,42,21,0,99,100,5,2,0,
        0,100,101,3,26,13,0,101,102,5,2,0,0,102,103,3,30,15,0,103,104,5,
        5,0,0,104,9,1,0,0,0,105,106,5,7,0,0,106,107,3,32,16,0,107,108,5,
        8,0,0,108,109,3,38,19,0,109,110,5,2,0,0,110,111,3,40,20,0,111,112,
        5,2,0,0,112,113,3,34,17,0,113,114,5,5,0,0,114,11,1,0,0,0,115,116,
        5,9,0,0,116,117,3,32,16,0,117,118,5,8,0,0,118,119,3,38,19,0,119,
        120,5,2,0,0,120,121,3,40,20,0,121,122,5,2,0,0,122,123,3,34,17,0,
        123,124,5,5,0,0,124,13,1,0,0,0,125,126,5,10,0,0,126,127,3,32,16,
        0,127,128,5,8,0,0,128,129,3,38,19,0,129,130,5,2,0,0,130,131,3,40,
        20,0,131,132,5,2,0,0,132,133,3,34,17,0,133,134,5,5,0,0,134,15,1,
        0,0,0,135,136,5,11,0,0,136,17,1,0,0,0,137,138,5,12,0,0,138,139,3,
        38,19,0,139,140,5,13,0,0,140,141,5,14,0,0,141,142,5,27,0,0,142,143,
        3,32,16,0,143,144,5,15,0,0,144,19,1,0,0,0,145,146,5,4,0,0,146,147,
        3,38,19,0,147,148,5,2,0,0,148,149,3,32,16,0,149,150,5,5,0,0,150,
        159,1,0,0,0,151,152,5,4,0,0,152,153,3,32,16,0,153,154,5,2,0,0,154,
        155,3,38,19,0,155,156,5,5,0,0,156,159,1,0,0,0,157,159,3,22,11,0,
        158,145,1,0,0,0,158,151,1,0,0,0,158,157,1,0,0,0,159,21,1,0,0,0,160,
        161,5,16,0,0,161,162,3,38,19,0,162,163,5,2,0,0,163,164,3,36,18,0,
        164,165,5,2,0,0,165,166,3,32,16,0,166,167,5,5,0,0,167,23,1,0,0,0,
        168,170,5,17,0,0,169,171,3,20,10,0,170,169,1,0,0,0,170,171,1,0,0,
        0,171,176,1,0,0,0,172,173,5,2,0,0,173,175,3,20,10,0,174,172,1,0,
        0,0,175,178,1,0,0,0,176,174,1,0,0,0,176,177,1,0,0,0,177,179,1,0,
        0,0,178,176,1,0,0,0,179,180,5,18,0,0,180,25,1,0,0,0,181,182,3,24,
        12,0,182,183,5,8,0,0,183,184,3,24,12,0,184,27,1,0,0,0,185,187,5,
        17,0,0,186,188,3,36,18,0,187,186,1,0,0,0,187,188,1,0,0,0,188,193,
        1,0,0,0,189,190,5,2,0,0,190,192,3,36,18,0,191,189,1,0,0,0,192,195,
        1,0,0,0,193,191,1,0,0,0,193,194,1,0,0,0,194,196,1,0,0,0,195,193,
        1,0,0,0,196,199,5,18,0,0,197,199,5,29,0,0,198,185,1,0,0,0,198,197,
        1,0,0,0,199,29,1,0,0,0,200,201,3,28,14,0,201,31,1,0,0,0,202,203,
        6,16,-1,0,203,204,5,20,0,0,204,228,5,29,0,0,205,209,5,29,0,0,206,
        207,5,12,0,0,207,208,5,29,0,0,208,210,5,15,0,0,209,206,1,0,0,0,209,
        210,1,0,0,0,210,228,1,0,0,0,211,228,5,28,0,0,212,228,5,25,0,0,213,
        228,5,26,0,0,214,215,5,4,0,0,215,216,3,32,16,0,216,217,5,2,0,0,217,
        222,3,32,16,0,218,219,5,2,0,0,219,221,3,32,16,0,220,218,1,0,0,0,
        221,224,1,0,0,0,222,220,1,0,0,0,222,223,1,0,0,0,223,225,1,0,0,0,
        224,222,1,0,0,0,225,226,5,5,0,0,226,228,1,0,0,0,227,202,1,0,0,0,
        227,205,1,0,0,0,227,211,1,0,0,0,227,212,1,0,0,0,227,213,1,0,0,0,
        227,214,1,0,0,0,228,234,1,0,0,0,229,230,10,7,0,0,230,231,5,19,0,
        0,231,233,3,32,16,8,232,229,1,0,0,0,233,236,1,0,0,0,234,232,1,0,
        0,0,234,235,1,0,0,0,235,33,1,0,0,0,236,234,1,0,0,0,237,238,3,28,
        14,0,238,35,1,0,0,0,239,240,5,29,0,0,240,37,1,0,0,0,241,242,5,29,
        0,0,242,39,1,0,0,0,243,244,5,29,0,0,244,41,1,0,0,0,245,246,5,29,
        0,0,246,43,1,0,0,0,16,49,71,82,85,87,95,158,170,176,187,193,198,
        209,222,227,234
    ]

class SWIRLParser ( Parser ):

    grammarFileName = "SWIRL.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'<'", "','", "'>'", "'('", "')'", "'exec('",
                     "'send('", "'->'", "'recv('", "'move('", "'end()'",
                     "'['", "'has'", "'data'", "']'", "'U('", "'{'", "'}'",
                     "'/'", "'?'", "'!'", "'+'", "'|'", "'.'", "'eof'",
                     "'begin'", "'in'", "'0'" ]

    symbolicNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>",
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>",
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>",
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>",
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>",
                      "<INVALID>", "REPL", "CHOICE", "PAR", "SEQ", "EOF_VAL",
                      "BEGIN_VAL", "IN", "ZERO", "ID", "WS", "COMMENT",
                      "BLOCK_COMMENT" ]

    RULE_workflow = 0
    RULE_location = 1
    RULE_trace = 2
    RULE_pred = 3
    RULE_exec = 4
    RULE_send = 5
    RULE_recv = 6
    RULE_move = 7
    RULE_end = 8
    RULE_guard = 9
    RULE_dataPair = 10
    RULE_collection = 11
    RULE_dataSet = 12
    RULE_flow = 13
    RULE_locationSet = 14
    RULE_mapping = 15
    RULE_data = 16
    RULE_dst = 17
    RULE_name = 18
    RULE_port = 19
    RULE_src = 20
    RULE_step = 21

    ruleNames =  [ "workflow", "location", "trace", "pred", "exec", "send",
                   "recv", "move", "end", "guard", "dataPair", "collection",
                   "dataSet", "flow", "locationSet", "mapping", "data",
                   "dst", "name", "port", "src", "step" ]

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
    T__19=20
    REPL=21
    CHOICE=22
    PAR=23
    SEQ=24
    EOF_VAL=25
    BEGIN_VAL=26
    IN=27
    ZERO=28
    ID=29
    WS=30
    COMMENT=31
    BLOCK_COMMENT=32

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
            self.state = 44
            self.location()
            self.state = 49
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==23:
                self.state = 45
                self.match(SWIRLParser.PAR)
                self.state = 46
                self.location()
                self.state = 51
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 52
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
            self.state = 54
            self.match(SWIRLParser.T__0)
            self.state = 55
            self.name()
            self.state = 56
            self.match(SWIRLParser.T__1)
            self.state = 57
            self.dataSet()
            self.state = 58
            self.match(SWIRLParser.T__1)
            self.state = 59
            self.trace(0)
            self.state = 60
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
            self.state = 71
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [21]:
                localctx = SWIRLParser.TraceReplContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 63
                self.match(SWIRLParser.REPL)
                self.state = 64
                self.trace(7)
                pass
            elif token in [6, 7, 9, 10, 11]:
                localctx = SWIRLParser.TracePredContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 65
                self.pred()
                pass
            elif token in [28]:
                localctx = SWIRLParser.TraceZeroContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 66
                self.match(SWIRLParser.ZERO)
                pass
            elif token in [4]:
                localctx = SWIRLParser.TraceParenContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 67
                self.match(SWIRLParser.T__3)
                self.state = 68
                self.trace(0)
                self.state = 69
                self.match(SWIRLParser.T__4)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 87
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,4,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 85
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,3,self._ctx)
                    if la_ == 1:
                        localctx = SWIRLParser.TraceOpContext(self, SWIRLParser.TraceContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_trace)
                        self.state = 73
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 74
                        localctx.op = self.match(SWIRLParser.SEQ)
                        self.state = 75
                        self.trace(7)
                        pass

                    elif la_ == 2:
                        localctx = SWIRLParser.TraceOpContext(self, SWIRLParser.TraceContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_trace)
                        self.state = 76
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 77
                        localctx.op = self.match(SWIRLParser.PAR)
                        self.state = 78
                        self.trace(6)
                        pass

                    elif la_ == 3:
                        localctx = SWIRLParser.TraceOpContext(self, SWIRLParser.TraceContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_trace)
                        self.state = 79
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 80
                        localctx.op = self.match(SWIRLParser.CHOICE)
                        self.state = 82
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if _la==12:
                            self.state = 81
                            self.guard()


                        self.state = 84
                        self.trace(5)
                        pass


                self.state = 89
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


        def end(self):
            return self.getTypedRuleContext(SWIRLParser.EndContext,0)


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
            self.state = 95
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6]:
                self.enterOuterAlt(localctx, 1)
                self.state = 90
                self.exec()
                pass
            elif token in [7]:
                self.enterOuterAlt(localctx, 2)
                self.state = 91
                self.send()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 3)
                self.state = 92
                self.recv()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 4)
                self.state = 93
                self.move()
                pass
            elif token in [11]:
                self.enterOuterAlt(localctx, 5)
                self.state = 94
                self.end()
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
            self.state = 97
            self.match(SWIRLParser.T__5)
            self.state = 98
            self.step()
            self.state = 99
            self.match(SWIRLParser.T__1)
            self.state = 100
            self.flow()
            self.state = 101
            self.match(SWIRLParser.T__1)
            self.state = 102
            self.mapping()
            self.state = 103
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
            self.state = 105
            self.match(SWIRLParser.T__6)
            self.state = 106
            self.data(0)
            self.state = 107
            self.match(SWIRLParser.T__7)
            self.state = 108
            self.port()
            self.state = 109
            self.match(SWIRLParser.T__1)
            self.state = 110
            self.src()
            self.state = 111
            self.match(SWIRLParser.T__1)
            self.state = 112
            self.dst()
            self.state = 113
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
            self.state = 115
            self.match(SWIRLParser.T__8)
            self.state = 116
            self.data(0)
            self.state = 117
            self.match(SWIRLParser.T__7)
            self.state = 118
            self.port()
            self.state = 119
            self.match(SWIRLParser.T__1)
            self.state = 120
            self.src()
            self.state = 121
            self.match(SWIRLParser.T__1)
            self.state = 122
            self.dst()
            self.state = 123
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
            self.state = 125
            self.match(SWIRLParser.T__9)
            self.state = 126
            self.data(0)
            self.state = 127
            self.match(SWIRLParser.T__7)
            self.state = 128
            self.port()
            self.state = 129
            self.match(SWIRLParser.T__1)
            self.state = 130
            self.src()
            self.state = 131
            self.match(SWIRLParser.T__1)
            self.state = 132
            self.dst()
            self.state = 133
            self.match(SWIRLParser.T__4)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EndContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return SWIRLParser.RULE_end

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterEnd" ):
                listener.enterEnd(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitEnd" ):
                listener.exitEnd(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEnd" ):
                return visitor.visitEnd(self)
            else:
                return visitor.visitChildren(self)




    def end(self):

        localctx = SWIRLParser.EndContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_end)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 135
            self.match(SWIRLParser.T__10)
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
        self.enterRule(localctx, 18, self.RULE_guard)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 137
            self.match(SWIRLParser.T__11)
            self.state = 138
            self.port()
            self.state = 139
            self.match(SWIRLParser.T__12)
            self.state = 140
            self.match(SWIRLParser.T__13)
            self.state = 141
            self.match(SWIRLParser.IN)
            self.state = 142
            self.data(0)
            self.state = 143
            self.match(SWIRLParser.T__14)
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
        self.enterRule(localctx, 20, self.RULE_dataPair)
        try:
            self.state = 158
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,6,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 145
                self.match(SWIRLParser.T__3)
                self.state = 146
                self.port()
                self.state = 147
                self.match(SWIRLParser.T__1)
                self.state = 148
                self.data(0)
                self.state = 149
                self.match(SWIRLParser.T__4)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 151
                self.match(SWIRLParser.T__3)
                self.state = 152
                self.data(0)
                self.state = 153
                self.match(SWIRLParser.T__1)
                self.state = 154
                self.port()
                self.state = 155
                self.match(SWIRLParser.T__4)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 157
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
        self.enterRule(localctx, 22, self.RULE_collection)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 160
            self.match(SWIRLParser.T__15)
            self.state = 161
            self.port()
            self.state = 162
            self.match(SWIRLParser.T__1)
            self.state = 163
            self.name()
            self.state = 164
            self.match(SWIRLParser.T__1)
            self.state = 165
            self.data(0)
            self.state = 166
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
        self.enterRule(localctx, 24, self.RULE_dataSet)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 168
            self.match(SWIRLParser.T__16)
            self.state = 170
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==4 or _la==16:
                self.state = 169
                self.dataPair()


            self.state = 176
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==2:
                self.state = 172
                self.match(SWIRLParser.T__1)
                self.state = 173
                self.dataPair()
                self.state = 178
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 179
            self.match(SWIRLParser.T__17)
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
        self.enterRule(localctx, 26, self.RULE_flow)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 181
            self.dataSet()
            self.state = 182
            self.match(SWIRLParser.T__7)
            self.state = 183
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
        self.enterRule(localctx, 28, self.RULE_locationSet)
        self._la = 0 # Token type
        try:
            self.state = 198
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [17]:
                self.enterOuterAlt(localctx, 1)
                self.state = 185
                self.match(SWIRLParser.T__16)
                self.state = 187
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==29:
                    self.state = 186
                    self.name()


                self.state = 193
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==2:
                    self.state = 189
                    self.match(SWIRLParser.T__1)
                    self.state = 190
                    self.name()
                    self.state = 195
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 196
                self.match(SWIRLParser.T__17)
                pass
            elif token in [29]:
                self.enterOuterAlt(localctx, 2)
                self.state = 197
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
        self.enterRule(localctx, 30, self.RULE_mapping)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 200
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
        _startState = 32
        self.enterRecursionRule(localctx, 32, self.RULE_data, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 227
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [20]:
                self.state = 203
                self.match(SWIRLParser.T__19)
                self.state = 204
                self.match(SWIRLParser.ID)
                pass
            elif token in [29]:
                self.state = 205
                self.match(SWIRLParser.ID)
                self.state = 209
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
                if la_ == 1:
                    self.state = 206
                    self.match(SWIRLParser.T__11)
                    self.state = 207
                    self.match(SWIRLParser.ID)
                    self.state = 208
                    self.match(SWIRLParser.T__14)


                pass
            elif token in [28]:
                self.state = 211
                self.match(SWIRLParser.ZERO)
                pass
            elif token in [25]:
                self.state = 212
                self.match(SWIRLParser.EOF_VAL)
                pass
            elif token in [26]:
                self.state = 213
                self.match(SWIRLParser.BEGIN_VAL)
                pass
            elif token in [4]:
                self.state = 214
                self.match(SWIRLParser.T__3)
                self.state = 215
                self.data(0)
                self.state = 216
                self.match(SWIRLParser.T__1)
                self.state = 217
                self.data(0)
                self.state = 222
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==2:
                    self.state = 218
                    self.match(SWIRLParser.T__1)
                    self.state = 219
                    self.data(0)
                    self.state = 224
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 225
                self.match(SWIRLParser.T__4)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 234
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,15,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = SWIRLParser.DataContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_data)
                    self.state = 229
                    if not self.precpred(self._ctx, 7):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 7)")
                    self.state = 230
                    self.match(SWIRLParser.T__18)
                    self.state = 231
                    self.data(8)
                self.state = 236
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,15,self._ctx)

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
        self.enterRule(localctx, 34, self.RULE_dst)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 237
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
        self.enterRule(localctx, 36, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 239
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
        self.enterRule(localctx, 38, self.RULE_port)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 241
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
        self.enterRule(localctx, 40, self.RULE_src)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 243
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
        self.enterRule(localctx, 42, self.RULE_step)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 245
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
        self._predicates[16] = self.data_sempred
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





