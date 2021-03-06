import { RegExpForeignCodeExtractor } from '../../extractors/regexp';
import { IForeignCodeExtractorsRegistry } from '../../extractors/types';

export const SQL_URL_PATTERN = '(?:(?:.*?)://(?:.*))';
// note: -a/--connection_arguments and -f/--file are not supported yet
const single_argument_options = [
  '--destination_table',
  '--project',
  '--use_bqstorage_api',
  '--use_rest_api',
  '--use_legacy_sql',
  '--verbose',
  '--params'
];
const zero_argument_options = ['-l', '--connections'];

const COMMAND_PATTERN =
  '(?:' +
  (zero_argument_options.join('|') +
    '|' +
    single_argument_options.map(command => command + ' \\w+').join('|')) +
  ')';

export let foreign_code_extractors: IForeignCodeExtractorsRegistry = {
  // general note: to match new lines use [^] instead of dot, unless the target is ES2018, then use /s
  python: [
    new RegExpForeignCodeExtractor({
      language: 'sql',
      pattern: `^%%bigquery(?: (?:${SQL_URL_PATTERN}|${COMMAND_PATTERN}|(?:\\w+ << )|(?:\\w+@\\w+)))?\n?((?:.+\n)?(?:[^]*))`,
      foreign_capture_groups: [1],
      is_standalone: true,
      file_extension: 'sql'
    })
  ]
};
