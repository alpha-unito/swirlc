# Generated from /home/tommo/Coding/Alpha/swirlc/grammar/SWIRL.g4 by ANTLR 4.13.1
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
        4,1,25,194,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,1,0,1,0,1,0,5,
        0,42,8,0,10,0,12,0,45,9,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
        1,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,3,2,66,8,2,1,2,1,2,1,2,5,2,
        71,8,2,10,2,12,2,74,9,2,1,3,1,3,1,3,1,3,3,3,80,8,3,1,4,1,4,1,4,1,
        4,1,4,1,4,1,4,1,4,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,5,1,6,1,
        6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,
        7,1,7,1,7,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,3,8,132,
        8,8,1,9,1,9,3,9,136,8,9,1,9,1,9,5,9,140,8,9,10,9,12,9,143,9,9,1,
        9,1,9,1,10,1,10,1,10,1,10,1,11,1,11,3,11,153,8,11,1,11,1,11,5,11,
        157,8,11,10,11,12,11,160,9,11,1,11,1,11,3,11,164,8,11,1,12,1,12,
        1,13,1,13,1,13,1,13,3,13,172,8,13,1,13,1,13,1,13,1,13,1,13,1,13,
        1,13,1,13,3,13,182,8,13,1,14,1,14,1,15,1,15,1,16,1,16,1,17,1,17,
        1,18,1,18,1,18,0,1,4,19,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,
        30,32,34,36,0,1,1,0,16,18,192,0,38,1,0,0,0,2,48,1,0,0,0,4,65,1,0,
        0,0,6,79,1,0,0,0,8,81,1,0,0,0,10,89,1,0,0,0,12,99,1,0,0,0,14,109,
        1,0,0,0,16,131,1,0,0,0,18,133,1,0,0,0,20,146,1,0,0,0,22,163,1,0,
        0,0,24,165,1,0,0,0,26,181,1,0,0,0,28,183,1,0,0,0,30,185,1,0,0,0,
        32,187,1,0,0,0,34,189,1,0,0,0,36,191,1,0,0,0,38,43,3,2,1,0,39,40,
        5,17,0,0,40,42,3,2,1,0,41,39,1,0,0,0,42,45,1,0,0,0,43,41,1,0,0,0,
        43,44,1,0,0,0,44,46,1,0,0,0,45,43,1,0,0,0,46,47,5,0,0,1,47,1,1,0,
        0,0,48,49,5,1,0,0,49,50,3,30,15,0,50,51,5,2,0,0,51,52,3,18,9,0,52,
        53,5,2,0,0,53,54,3,4,2,0,54,55,5,3,0,0,55,3,1,0,0,0,56,57,6,2,-1,
        0,57,58,5,15,0,0,58,66,3,4,2,5,59,66,3,6,3,0,60,66,5,21,0,0,61,62,
        5,4,0,0,62,63,3,4,2,0,63,64,5,5,0,0,64,66,1,0,0,0,65,56,1,0,0,0,
        65,59,1,0,0,0,65,60,1,0,0,0,65,61,1,0,0,0,66,72,1,0,0,0,67,68,10,
        4,0,0,68,69,7,0,0,0,69,71,3,4,2,5,70,67,1,0,0,0,71,74,1,0,0,0,72,
        70,1,0,0,0,72,73,1,0,0,0,73,5,1,0,0,0,74,72,1,0,0,0,75,80,3,8,4,
        0,76,80,3,10,5,0,77,80,3,12,6,0,78,80,3,14,7,0,79,75,1,0,0,0,79,
        76,1,0,0,0,79,77,1,0,0,0,79,78,1,0,0,0,80,7,1,0,0,0,81,82,5,6,0,
        0,82,83,3,36,18,0,83,84,5,2,0,0,84,85,3,20,10,0,85,86,5,2,0,0,86,
        87,3,24,12,0,87,88,5,5,0,0,88,9,1,0,0,0,89,90,5,7,0,0,90,91,3,26,
        13,0,91,92,5,8,0,0,92,93,3,32,16,0,93,94,5,2,0,0,94,95,3,34,17,0,
        95,96,5,2,0,0,96,97,3,28,14,0,97,98,5,5,0,0,98,11,1,0,0,0,99,100,
        5,9,0,0,100,101,3,26,13,0,101,102,5,8,0,0,102,103,3,32,16,0,103,
        104,5,2,0,0,104,105,3,34,17,0,105,106,5,2,0,0,106,107,3,28,14,0,
        107,108,5,5,0,0,108,13,1,0,0,0,109,110,5,10,0,0,110,111,3,26,13,
        0,111,112,5,8,0,0,112,113,3,32,16,0,113,114,5,2,0,0,114,115,3,34,
        17,0,115,116,5,2,0,0,116,117,3,28,14,0,117,118,5,5,0,0,118,15,1,
        0,0,0,119,120,5,4,0,0,120,121,3,32,16,0,121,122,5,2,0,0,122,123,
        3,26,13,0,123,124,5,5,0,0,124,132,1,0,0,0,125,126,5,4,0,0,126,127,
        3,26,13,0,127,128,5,2,0,0,128,129,3,32,16,0,129,130,5,5,0,0,130,
        132,1,0,0,0,131,119,1,0,0,0,131,125,1,0,0,0,132,17,1,0,0,0,133,135,
        5,11,0,0,134,136,3,16,8,0,135,134,1,0,0,0,135,136,1,0,0,0,136,141,
        1,0,0,0,137,138,5,2,0,0,138,140,3,16,8,0,139,137,1,0,0,0,140,143,
        1,0,0,0,141,139,1,0,0,0,141,142,1,0,0,0,142,144,1,0,0,0,143,141,
        1,0,0,0,144,145,5,12,0,0,145,19,1,0,0,0,146,147,3,18,9,0,147,148,
        5,8,0,0,148,149,3,18,9,0,149,21,1,0,0,0,150,152,5,11,0,0,151,153,
        3,30,15,0,152,151,1,0,0,0,152,153,1,0,0,0,153,158,1,0,0,0,154,155,
        5,2,0,0,155,157,3,30,15,0,156,154,1,0,0,0,157,160,1,0,0,0,158,156,
        1,0,0,0,158,159,1,0,0,0,159,161,1,0,0,0,160,158,1,0,0,0,161,164,
        5,12,0,0,162,164,5,22,0,0,163,150,1,0,0,0,163,162,1,0,0,0,164,23,
        1,0,0,0,165,166,3,22,11,0,166,25,1,0,0,0,167,171,5,22,0,0,168,169,
        5,13,0,0,169,170,5,22,0,0,170,172,5,14,0,0,171,168,1,0,0,0,171,172,
        1,0,0,0,172,182,1,0,0,0,173,182,5,21,0,0,174,182,5,19,0,0,175,176,
        5,4,0,0,176,177,3,26,13,0,177,178,5,2,0,0,178,179,3,26,13,0,179,
        180,5,5,0,0,180,182,1,0,0,0,181,167,1,0,0,0,181,173,1,0,0,0,181,
        174,1,0,0,0,181,175,1,0,0,0,182,27,1,0,0,0,183,184,3,22,11,0,184,
        29,1,0,0,0,185,186,5,22,0,0,186,31,1,0,0,0,187,188,5,22,0,0,188,
        33,1,0,0,0,189,190,5,22,0,0,190,35,1,0,0,0,191,192,5,22,0,0,192,
        37,1,0,0,0,12,43,65,72,79,131,135,141,152,158,163,171,181
    ]

class SWIRLParser ( Parser ):

    grammarFileName = "SWIRL.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'<'", "','", "'>'", "'('", "')'", "'exec('", 
                     "'send('", "'->'", "'recv('", "'move('", "'{'", "'}'", 
                     "'['", "']'", "'!'", "'+'", "'|'", "'.'", "'eof'", 
                     "'in'", "'0'" ]

    symbolicNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "REPL", "CHOICE", 
                      "PAR", "SEQ", "EOF_VAL", "IN", "ZERO", "ID", "WS", 
                      "COMMENT", "BLOCK_COMMENT" ]

    RULE_workflow = 0
    RULE_location = 1
    RULE_trace = 2
    RULE_pred = 3
    RULE_exec = 4
    RULE_send = 5
    RULE_recv = 6
    RULE_move = 7
    RULE_dataPair = 8
    RULE_dataSet = 9
    RULE_flow = 10
    RULE_locationSet = 11
    RULE_mapping = 12
    RULE_data = 13
    RULE_dst = 14
    RULE_name = 15
    RULE_port = 16
    RULE_src = 17
    RULE_step = 18

    ruleNames =  [ "workflow", "location", "trace", "pred", "exec", "send", 
                   "recv", "move", "dataPair", "dataSet", "flow", "locationSet", 
                   "mapping", "data", "dst", "name", "port", "src", "step" ]

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
    REPL=15
    CHOICE=16
    PAR=17
    SEQ=18
    EOF_VAL=19
    IN=20
    ZERO=21
    ID=22
    WS=23
    COMMENT=24
    BLOCK_COMMENT=25

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.1")
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
            self.state = 38
            self.location()
            self.state = 43
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==17:
                self.state = 39
                self.match(SWIRLParser.PAR)
                self.state = 40
                self.location()
                self.state = 45
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 46
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
            self.state = 48
            self.match(SWIRLParser.T__0)
            self.state = 49
            self.name()
            self.state = 50
            self.match(SWIRLParser.T__1)
            self.state = 51
            self.dataSet()
            self.state = 52
            self.match(SWIRLParser.T__1)
            self.state = 53
            self.trace(0)
            self.state = 54
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

        def CHOICE(self):
            return self.getToken(SWIRLParser.CHOICE, 0)
        def PAR(self):
            return self.getToken(SWIRLParser.PAR, 0)
        def SEQ(self):
            return self.getToken(SWIRLParser.SEQ, 0)

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
            self.state = 65
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [15]:
                localctx = SWIRLParser.TraceReplContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 57
                self.match(SWIRLParser.REPL)
                self.state = 58
                self.trace(5)
                pass
            elif token in [6, 7, 9, 10]:
                localctx = SWIRLParser.TracePredContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 59
                self.pred()
                pass
            elif token in [21]:
                localctx = SWIRLParser.TraceZeroContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 60
                self.match(SWIRLParser.ZERO)
                pass
            elif token in [4]:
                localctx = SWIRLParser.TraceParenContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 61
                self.match(SWIRLParser.T__3)
                self.state = 62
                self.trace(0)
                self.state = 63
                self.match(SWIRLParser.T__4)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 72
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,2,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = SWIRLParser.TraceOpContext(self, SWIRLParser.TraceContext(self, _parentctx, _parentState))
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_trace)
                    self.state = 67
                    if not self.precpred(self._ctx, 4):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                    self.state = 68
                    localctx.op = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 458752) != 0)):
                        localctx.op = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 69
                    self.trace(5) 
                self.state = 74
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,2,self._ctx)

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
            self.state = 79
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6]:
                self.enterOuterAlt(localctx, 1)
                self.state = 75
                self.exec()
                pass
            elif token in [7]:
                self.enterOuterAlt(localctx, 2)
                self.state = 76
                self.send()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 3)
                self.state = 77
                self.recv()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 4)
                self.state = 78
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
            self.state = 81
            self.match(SWIRLParser.T__5)
            self.state = 82
            self.step()
            self.state = 83
            self.match(SWIRLParser.T__1)
            self.state = 84
            self.flow()
            self.state = 85
            self.match(SWIRLParser.T__1)
            self.state = 86
            self.mapping()
            self.state = 87
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
            self.state = 89
            self.match(SWIRLParser.T__6)
            self.state = 90
            self.data()
            self.state = 91
            self.match(SWIRLParser.T__7)
            self.state = 92
            self.port()
            self.state = 93
            self.match(SWIRLParser.T__1)
            self.state = 94
            self.src()
            self.state = 95
            self.match(SWIRLParser.T__1)
            self.state = 96
            self.dst()
            self.state = 97
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
            self.state = 99
            self.match(SWIRLParser.T__8)
            self.state = 100
            self.data()
            self.state = 101
            self.match(SWIRLParser.T__7)
            self.state = 102
            self.port()
            self.state = 103
            self.match(SWIRLParser.T__1)
            self.state = 104
            self.src()
            self.state = 105
            self.match(SWIRLParser.T__1)
            self.state = 106
            self.dst()
            self.state = 107
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
            self.state = 109
            self.match(SWIRLParser.T__9)
            self.state = 110
            self.data()
            self.state = 111
            self.match(SWIRLParser.T__7)
            self.state = 112
            self.port()
            self.state = 113
            self.match(SWIRLParser.T__1)
            self.state = 114
            self.src()
            self.state = 115
            self.match(SWIRLParser.T__1)
            self.state = 116
            self.dst()
            self.state = 117
            self.match(SWIRLParser.T__4)
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
        self.enterRule(localctx, 16, self.RULE_dataPair)
        try:
            self.state = 131
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,4,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 119
                self.match(SWIRLParser.T__3)
                self.state = 120
                self.port()
                self.state = 121
                self.match(SWIRLParser.T__1)
                self.state = 122
                self.data()
                self.state = 123
                self.match(SWIRLParser.T__4)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 125
                self.match(SWIRLParser.T__3)
                self.state = 126
                self.data()
                self.state = 127
                self.match(SWIRLParser.T__1)
                self.state = 128
                self.port()
                self.state = 129
                self.match(SWIRLParser.T__4)
                pass


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
        self.enterRule(localctx, 18, self.RULE_dataSet)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 133
            self.match(SWIRLParser.T__10)
            self.state = 135
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==4:
                self.state = 134
                self.dataPair()


            self.state = 141
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==2:
                self.state = 137
                self.match(SWIRLParser.T__1)
                self.state = 138
                self.dataPair()
                self.state = 143
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 144
            self.match(SWIRLParser.T__11)
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
        self.enterRule(localctx, 20, self.RULE_flow)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 146
            self.dataSet()
            self.state = 147
            self.match(SWIRLParser.T__7)
            self.state = 148
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
        self.enterRule(localctx, 22, self.RULE_locationSet)
        self._la = 0 # Token type
        try:
            self.state = 163
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [11]:
                self.enterOuterAlt(localctx, 1)
                self.state = 150
                self.match(SWIRLParser.T__10)
                self.state = 152
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==22:
                    self.state = 151
                    self.name()


                self.state = 158
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==2:
                    self.state = 154
                    self.match(SWIRLParser.T__1)
                    self.state = 155
                    self.name()
                    self.state = 160
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 161
                self.match(SWIRLParser.T__11)
                pass
            elif token in [22]:
                self.enterOuterAlt(localctx, 2)
                self.state = 162
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
        self.enterRule(localctx, 24, self.RULE_mapping)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 165
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




    def data(self):

        localctx = SWIRLParser.DataContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_data)
        self._la = 0 # Token type
        try:
            self.state = 181
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [22]:
                self.enterOuterAlt(localctx, 1)
                self.state = 167
                self.match(SWIRLParser.ID)
                self.state = 171
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==13:
                    self.state = 168
                    self.match(SWIRLParser.T__12)
                    self.state = 169
                    self.match(SWIRLParser.ID)
                    self.state = 170
                    self.match(SWIRLParser.T__13)


                pass
            elif token in [21]:
                self.enterOuterAlt(localctx, 2)
                self.state = 173
                self.match(SWIRLParser.ZERO)
                pass
            elif token in [19]:
                self.enterOuterAlt(localctx, 3)
                self.state = 174
                self.match(SWIRLParser.EOF_VAL)
                pass
            elif token in [4]:
                self.enterOuterAlt(localctx, 4)
                self.state = 175
                self.match(SWIRLParser.T__3)
                self.state = 176
                self.data()
                self.state = 177
                self.match(SWIRLParser.T__1)
                self.state = 178
                self.data()
                self.state = 179
                self.match(SWIRLParser.T__4)
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
        self.enterRule(localctx, 28, self.RULE_dst)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 183
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
        self.enterRule(localctx, 30, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 185
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
        self.enterRule(localctx, 32, self.RULE_port)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 187
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
        self.enterRule(localctx, 34, self.RULE_src)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 189
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
        self.enterRule(localctx, 36, self.RULE_step)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 191
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
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def trace_sempred(self, localctx:TraceContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 4)
         




