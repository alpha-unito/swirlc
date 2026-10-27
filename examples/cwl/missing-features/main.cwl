cwlVersion: v1.2
class: Workflow
requirements:
  InlineJavascriptRequirement: {}
  MultipleInputFeatureRequirement: {}
  StepInputExpressionRequirement: {}
inputs:
  items:
    type: {type: array, items: {$import: item.yml}}
  enabled: boolean
  status: int
outputs:
  report:
    type: File
    outputSource: inspect/report
  code:
    type: int
    outputSource: inspect/code
  ok:
    type: boolean
    outputSource: check/ok
steps:
  generate:
    in: {items: items}
    out: [message, artifact]
    run:
      class: CommandLineTool
      inputs:
        items:
          type: {type: array, items: {$import: item.yml}}
      outputs:
        message: string
        artifact:
          type: File
          secondaryFiles: .meta
      requirements:
        InitialWorkDirRequirement:
          listing:
            - entry: $(inputs.items.map(function(item) { return item.source; }))
            - entryname: generate.py
              entry: |
                import json, sys
                from pathlib import Path
                item = json.loads(sys.argv[1])[0]
                source = Path(item["source"]["basename"])
                Path("value.txt").write_text(item["name"] + ":" + source.read_text().strip())
                Path("value.txt.meta").write_text(Path(str(source) + ".meta").read_text())
                Path("cwl.output.json").write_text(json.dumps({
                    "message": "generated", "artifact": {
                        "class": "File", "path": "value.txt", "secondaryFiles": [
                            {"class": "File", "path": "value.txt.meta"}]}}))
      baseCommand: [python3, generate.py]
      arguments: [$(JSON.stringify(inputs.items))]
  optional:
    in:
      message: generate/message
      enabled: enabled
    when: $(inputs.enabled)
    out: [value]
    run:
      class: ExpressionTool
      inputs: {message: string}
      outputs: {value: string}
      expression: '${ return {value: inputs.message}; }'
  inspect:
    in:
      file: generate/artifact
      bundle:
        valueFrom: |
          ${ return {'class': 'Directory', basename: 'bundle', listing: [[inputs.file]].flat()}; }
      messages:
        source: [generate/message, optional/value]
        pickValue: all_non_null
      status: status
    out: [report, code]
    run:
      class: CommandLineTool
      inputs:
        file:
          type: File
          secondaryFiles: .meta
        bundle: Directory
        messages: string[]
        status:
          type: int
          inputBinding: {position: 1}
      outputs:
        report: stdout
        code:
          type: int
          outputBinding: {outputEval: $(runtime.exitCode)}
      requirements:
        InitialWorkDirRequirement:
          listing:
            - entry: $(inputs.bundle)
            - entryname: messages.json
              entry: $(JSON.stringify(inputs.messages))
            - entryname: inspect.py
              entry: |
                import json, sys
                from pathlib import Path
                print(json.dumps({
                    "text": Path("bundle/value.txt").read_text(),
                    "meta": Path("bundle/value.txt.meta").read_text().strip(),
                    "messages": json.loads(Path("messages.json").read_text()),
                    "marker": "expected"}))
                sys.exit(int(sys.argv[1]))
      baseCommand: [python3, inspect.py]
      stdout: report.json
      successCodes: [0, 1]
  check:
    in: {log: inspect/report, code: inspect/code}
    out: [ok]
    run:
      class: ExpressionTool
      inputs:
        log: {type: File, loadContents: true}
        code: int
      outputs: {ok: boolean}
      expression: |
        ${
          if (!Number.isInteger(inputs.code) || (inputs.code !== 0 && inputs.code !== 1) ||
              !inputs.log.contents.includes('"marker": "expected"')) {
            throw new Error('Unexpected exit status or log: ' + inputs.log.contents);
          }
          return {ok: true};
        }
